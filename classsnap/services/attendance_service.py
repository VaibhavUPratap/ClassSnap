"""Transactional attendance session lifecycle."""

from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from classsnap.exceptions import ResourceNotFoundError, ValidationError
from classsnap.models.attendance import (
    AttendanceDetection,
    AttendanceRecord,
    AttendanceSession,
    ProposedMatch,
    ReviewDecision,
)
from classsnap.models.audit import AuditEvent


class AttendanceService:
    """Creates, reviews, and confirms attendance sessions."""

    @staticmethod
    def create_session(
        db: Session,
        name: str,
        actor: str = "system",
        class_at: datetime | None = None,
    ) -> AttendanceSession:
        session = AttendanceSession(
            name=name,
            created_by=actor,
            status="draft",
            class_at=class_at or datetime.now(timezone.utc),
        )
        db.add(session)
        db.flush()
        AttendanceService._audit(db, "SESSION_CREATED", session.id, actor)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session(db: Session, session_id: str) -> AttendanceSession:
        return AttendanceService._get(db, session_id)

    @staticmethod
    def begin_processing(db: Session, session_id: str) -> AttendanceSession:
        session = AttendanceService._get(db, session_id)
        AttendanceService._require_status(session, {"draft"})
        session.status = "processing"
        db.commit()
        return session

    @staticmethod
    def add_proposals(
        db: Session,
        session_id: str,
        proposals: Iterable[tuple[str, str, Optional[str], Optional[float], Optional[str]]],
        actor: str = "system",
    ) -> AttendanceSession:
        """Persist detection proposals and move the session to human review."""
        session = AttendanceService._get(db, session_id)
        AttendanceService._require_status(session, {"processing"})
        proposal_list = list(proposals)
        detection_ids = [proposal[0] for proposal in proposal_list]
        if len(detection_ids) != len(set(detection_ids)):
            raise ValidationError("A session cannot contain duplicate detection IDs")
        existing_ids = set(
            db.execute(
                select(AttendanceDetection.detection_id).where(
                    AttendanceDetection.session_id == session.id,
                    AttendanceDetection.detection_id.in_(detection_ids),
                )
            ).scalars()
        )
        if existing_ids:
            raise ValidationError(
                f"Detection IDs already submitted for this session: {sorted(existing_ids)}"
            )
        for sequence, (detection_id, status, student_id, similarity, reason) in enumerate(proposal_list):
            detection = AttendanceDetection(
                session_id=session.id,
                detection_id=detection_id,
                sequence=sequence,
                status=status,
            )
            detection.proposed_match = ProposedMatch(
                student_id=student_id,
                similarity=similarity,
                status=status,
                rejection_reason=reason,
            )
            db.add(detection)
        session.status = "review_required"
        AttendanceService._audit(db, "PROPOSALS_CREATED", session.id, actor)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def review_detection(
        db: Session,
        session_id: str,
        detection_id: str,
        student_id: Optional[str],
        present: bool,
        actor: str = "system",
        notes: Optional[str] = None,
    ) -> ProposedMatch:
        session = AttendanceService._get(db, session_id)
        AttendanceService._require_status(session, {"review_required"})
        detection = db.execute(
            select(AttendanceDetection).where(
                AttendanceDetection.session_id == session_id,
                AttendanceDetection.detection_id == detection_id,
            )
        ).scalar_one_or_none()
        if detection is None or detection.proposed_match is None:
            raise ResourceNotFoundError("Detection", detection_id)
        if present and not student_id:
            raise ValidationError("A present review decision requires a student identifier")
        match = detection.proposed_match
        db.add(
            ReviewDecision(
                session_id=session.id,
                detection_row_id=detection.id,
                reviewer=actor,
                decision="present" if present else "absent",
                original_student_id=match.student_id,
                selected_student_id=student_id if present else None,
                notes=notes,
            )
        )
        match.student_id = student_id if present else None
        match.reviewed = True
        match.status = "reviewed_present" if present else "reviewed_absent"
        match.rejection_reason = notes if not present else None
        db.commit()
        return match

    @staticmethod
    def confirm(db: Session, session_id: str, actor: str = "system") -> AttendanceSession:
        session = AttendanceService._get(db, session_id)
        AttendanceService._require_status(session, {"review_required"})
        matches = [d.proposed_match for d in session.detections if d.proposed_match]
        if any(not match.reviewed for match in matches):
            raise ValidationError("All proposed detections must be reviewed before confirmation")
        try:
            present_ids = {match.student_id for match in matches if match.student_id}
            for record in list(session.attendance):
                db.delete(record)
            for student_id in present_ids:
                db.add(AttendanceRecord(session_id=session.id, student_id=student_id, present=True))
            session.status = "confirmed"
            session.confirmed_at = datetime.now(timezone.utc)
            AttendanceService._audit(db, "SESSION_CONFIRMED", session.id, actor)
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(session)
        return session

    @staticmethod
    def correct_confirmed_attendance(
        db: Session,
        session_id: str,
        detection_id: str,
        student_id: Optional[str],
        present: bool,
        actor: str,
        reason: str,
    ) -> AttendanceSession:
        """Apply an auditable correction without reopening a finalized session."""
        session = AttendanceService._get(db, session_id)
        AttendanceService._require_status(session, {"confirmed"})
        if not actor.strip():
            raise ValidationError("A correction requires a reviewer identity")
        if not reason.strip():
            raise ValidationError("A correction requires a reason")
        if present and not student_id:
            raise ValidationError("A present correction requires a student identifier")

        detection = db.execute(
            select(AttendanceDetection).where(
                AttendanceDetection.session_id == session_id,
                AttendanceDetection.detection_id == detection_id,
            )
        ).scalar_one_or_none()
        if detection is None or detection.proposed_match is None:
            raise ResourceNotFoundError("Detection", detection_id)

        match = detection.proposed_match
        existing_target = None
        if student_id:
            existing_target = db.execute(
                select(AttendanceRecord).where(
                    AttendanceRecord.session_id == session_id,
                    AttendanceRecord.student_id == student_id,
                )
            ).scalar_one_or_none()
            if existing_target and existing_target.student_id != match.student_id:
                raise ValidationError(
                    f"Student '{student_id}' is already present in this session"
                )

        try:
            original_student_id = match.student_id
            if original_student_id and original_student_id != student_id:
                old_record = db.execute(
                    select(AttendanceRecord).where(
                        AttendanceRecord.session_id == session_id,
                        AttendanceRecord.student_id == original_student_id,
                    )
                ).scalar_one_or_none()
                if old_record:
                    db.delete(old_record)

            if present and not existing_target and student_id:
                db.add(
                    AttendanceRecord(
                        session_id=session.id,
                        student_id=student_id,
                        present=True,
                        source="correction",
                    )
                )

            db.add(
                ReviewDecision(
                    session_id=session.id,
                    detection_row_id=detection.id,
                    reviewer=actor,
                    decision="correction_present" if present else "correction_absent",
                    original_student_id=original_student_id,
                    selected_student_id=student_id if present else None,
                    notes=reason,
                )
            )
            match.student_id = student_id if present else None
            match.status = "corrected_present" if present else "corrected_absent"
            match.rejection_reason = None if present else reason
            db.add(
                AuditEvent(
                    action="SESSION_ATTENDANCE_CORRECTED",
                    entity_type="attendance_session",
                    entity_id=session.id,
                    actor=actor,
                    details=reason,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(session)
        return session

    @staticmethod
    def _get(db: Session, session_id: str) -> AttendanceSession:
        session = db.get(AttendanceSession, session_id)
        if session is None:
            raise ResourceNotFoundError("Attendance session", session_id)
        return session

    @staticmethod
    def _require_status(session: AttendanceSession, allowed: set[str]) -> None:
        if session.status not in allowed:
            raise ValidationError(
                f"Session '{session.id}' is '{session.status}', expected one of {sorted(allowed)}"
            )

    @staticmethod
    def _audit(db: Session, action: str, entity_id: str, actor: str) -> None:
        db.add(AuditEvent(action=action, entity_type="attendance_session", entity_id=entity_id, actor=actor))
