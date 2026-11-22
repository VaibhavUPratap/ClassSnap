"""Transactional attendance session lifecycle.

Workflow
--------
1. ``create_session`` → ``begin_processing`` → ``add_proposals`` (image processed).
2. ``add_proposals`` stores one row per detected face *and* builds the proposed
   roster: every confidently, uniquely matched student is proposed PRESENT,
   ambiguous candidates are NEEDS_REVIEW, everyone else is NOT_DETECTED.
   Nothing is final yet.
3. The reviewer edits the proposal (``review_detection`` for a face,
   ``set_student_attendance`` for a roster row).
4. ``confirm`` validates the proposal and writes exactly one final
   ``AttendanceRecord`` per roster student inside a single transaction.
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Iterable, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from classsnap.exceptions import DatabaseError, ResourceNotFoundError, ValidationError
from classsnap.models.attendance import (
    FINAL_ABSENT,
    FINAL_PRESENT,
    FINAL_UNVERIFIED,
    PROPOSED_ABSENT,
    PROPOSED_NEEDS_REVIEW,
    PROPOSED_NOT_DETECTED,
    PROPOSED_PRESENT,
    AttendanceDetection,
    AttendanceRecord,
    AttendanceSession,
    ProposedAttendance,
    ProposedMatch,
    ReviewDecision,
)
from classsnap.models.audit import AuditEvent
from classsnap.models.student import Student

STATUS_MATCHED = "matched_pending_review"
_REJECTED_FACE_STATUSES = {"reviewed_absent", "corrected_absent"}

# How a final record was verified.
VERIFIED_BY_RECOGNITION = "face_recognition"
VERIFIED_BY_FACE_REVIEW = "manual_face_review"
VERIFIED_MANUALLY = "manual"
VERIFIED_UNRESOLVED = "unresolved"
VERIFIED_BY_CORRECTION = "manual_correction"

# A session may combine several classroom photos (e.g. front and back of the
# room). Each face belongs to one photo; a student may appear in many photos
# but at most once per photo.
MAX_PHOTOS_PER_SESSION = 10

ProposalTuple = Sequence  # (detection_id, status, student_id, similarity, reason[, candidate_student_id])


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AttendanceService:
    """Creates, reviews, and confirms attendance sessions."""

    # ------------------------------------------------------------------ setup

    @staticmethod
    def create_session(
        db: Session,
        name: str,
        actor: str = "system",
        class_at: datetime | None = None,
        class_section: str | None = None,
    ) -> AttendanceSession:
        session = AttendanceSession(
            name=name,
            created_by=actor,
            status="draft",
            class_at=class_at or datetime.now(timezone.utc),
            class_section=class_section,
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
    def delete_session(db: Session, session_id: str, actor: str = "system") -> None:
        """Permanently remove a session and everything recorded for it.

        Detections (with their stored face previews), proposals, review
        decisions and final attendance records are removed via ORM cascades.
        An audit event survives the deletion so the removal stays traceable.
        """
        session = AttendanceService._get(db, session_id)
        details = f"name={session.name!r}; status={session.status}"
        try:
            db.delete(session)
            AttendanceService._audit(db, "SESSION_DELETED", session_id, actor, details)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise

    @staticmethod
    def get_detection(db: Session, session_id: str, detection_id: str) -> AttendanceDetection:
        detection = db.execute(
            select(AttendanceDetection).where(
                AttendanceDetection.session_id == session_id,
                AttendanceDetection.detection_id == detection_id,
            )
        ).scalar_one_or_none()
        if detection is None:
            raise ResourceNotFoundError("Detection", detection_id)
        return detection

    @staticmethod
    def begin_processing(db: Session, session_id: str) -> AttendanceSession:
        session = AttendanceService._get(db, session_id)
        AttendanceService._require_status(session, {"draft"})
        session.status = "processing"
        db.commit()
        return session

    @staticmethod
    def require_image_upload_allowed(
        db: Session, session_id: str, photo_count: int = 1
    ) -> AttendanceSession:
        """Reject classroom photos before running the CV pipeline.

        Photos can be added while the session is processing or under review.
        Once attendance is confirmed the session is closed to new photos.
        """
        session = AttendanceService._get(db, session_id)
        if session.status == "confirmed":
            raise ValidationError(
                "Attendance for this session is already confirmed, so no more photos can be "
                "added. Create a new session to process another class."
            )
        AttendanceService._require_status(session, {"processing", "review_required"})
        if AttendanceService.photo_count(session) + photo_count > MAX_PHOTOS_PER_SESSION:
            raise ValidationError(
                f"A session can combine at most {MAX_PHOTOS_PER_SESSION} photos "
                f"({AttendanceService.photo_count(session)} already processed)."
            )
        return session

    @staticmethod
    def photo_count(session: AttendanceSession) -> int:
        """Number of classroom photos processed for the session."""
        # Sessions processed before multi-photo support stored no count but
        # always had exactly one photo once processed.
        legacy = 1 if session.status in {"review_required", "confirmed"} else 0
        return max(
            session.photo_count or 0,
            legacy,
            max((d.photo_index or 1 for d in session.detections), default=0),
        )

    # -------------------------------------------------------------- proposals

    @staticmethod
    def add_proposals(
        db: Session,
        session_id: str,
        proposals: Iterable[ProposalTuple],
        actor: str = "system",
    ) -> AttendanceSession:
        """Persist one photo's face proposals, update the proposed roster, and move to review.

        Calling it again while the session is under review adds another photo:
        its faces get the next ``photo_index`` and roster rows the reviewer has
        not touched are re-derived from the faces of every photo.
        """
        session = AttendanceService._get(db, session_id)
        AttendanceService._require_status(session, {"processing", "review_required"})
        adding_photo = session.status == "review_required"
        photo_index = AttendanceService.photo_count(session) + 1
        first_sequence = len(session.detections)
        proposal_list = [tuple(proposal) + (None,) * (6 - len(proposal)) for proposal in proposals]
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
        for sequence, (detection_id, status, student_id, similarity, reason, candidate_id) in enumerate(
            proposal_list
        ):
            detection = AttendanceDetection(
                session_id=session.id,
                detection_id=detection_id,
                sequence=first_sequence + sequence,
                photo_index=photo_index,
                status=status,
            )
            detection.proposed_match = ProposedMatch(
                student_id=student_id,
                similarity=similarity,
                status=status,
                rejection_reason=reason,
                candidate_student_id=candidate_id,
            )
            db.add(detection)
        session.photo_count = photo_index
        db.flush()
        db.refresh(session)
        AttendanceService._build_proposed_attendance(db, session, refresh_untouched=adding_photo)
        session.status = "review_required"
        AttendanceService._audit(
            db, "PROPOSALS_CREATED", session.id, actor, f"photo={photo_index}; faces={len(proposal_list)}"
        )
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def roster_students(db: Session, class_section: Optional[str] = None) -> list[Student]:
        """Active students forming a session roster (one class, or everyone)."""
        statement = select(Student).where(Student.is_active.is_(True))
        if class_section:
            statement = statement.where(Student.class_section == class_section)
        return list(db.execute(statement.order_by(Student.student_id)).scalars())

    @staticmethod
    def _build_proposed_attendance(
        db: Session, session: AttendanceSession, refresh_untouched: bool = False
    ) -> None:
        """Create a proposed row for every active roster student that lacks one.

        With ``refresh_untouched`` (a photo was added), rows the reviewer has
        not changed are re-derived from the faces of all photos as well.
        """
        existing_rows = {row.student_id: row for row in session.proposed_attendance}
        existing = set(existing_rows)
        roster = {
            student.id for student in AttendanceService.roster_students(db, session.class_section)
        }

        # student -> photo -> faces confidently matched to them in that photo
        matched: dict[str, dict[int, list[AttendanceDetection]]] = {}
        candidates: dict[str, AttendanceDetection] = {}
        for detection in session.detections:
            match = detection.proposed_match
            if match is None:
                continue
            if match.status == STATUS_MATCHED and match.student_id:
                matched.setdefault(match.student_id, {}).setdefault(
                    detection.photo_index or 1, []
                ).append(detection)
            elif match.candidate_student_id and not match.student_id:
                current = candidates.get(match.candidate_student_id)
                if current is None or (match.similarity or 0) > (current.proposed_match.similarity or 0):
                    candidates[match.candidate_student_id] = detection

        def proposal_for(student_id):
            per_photo = matched.get(student_id, {})
            if any(len(faces) > 1 for faces in per_photo.values()):
                # Defensive: the matcher guarantees uniqueness within a photo,
                # but never auto-mark a student assigned to two faces of one photo.
                return None, PROPOSED_NEEDS_REVIEW, None
            if per_photo:
                # Confident, unique identification in at least one photo →
                # proposed PRESENT, backed by the strongest of those faces.
                detection = max(
                    (faces[0] for faces in per_photo.values()),
                    key=lambda d: d.proposed_match.similarity or 0,
                )
                return detection, PROPOSED_PRESENT, detection.proposed_match.similarity
            if student_id in candidates:
                detection = candidates[student_id]
                return detection, PROPOSED_NEEDS_REVIEW, detection.proposed_match.similarity
            return None, PROPOSED_NOT_DETECTED, None

        if refresh_untouched:
            for student_id in sorted(roster & existing):
                row = existing_rows[student_id]
                if row.manually_set:
                    continue
                detection, status, similarity = proposal_for(student_id)
                row.status = row.auto_status = status
                row.detection_row_id = detection.id if detection else None
                row.similarity = similarity

        for student_id in sorted(roster - existing):
            detection, status, similarity = proposal_for(student_id)
            db.add(
                ProposedAttendance(
                    session_id=session.id,
                    student_id=student_id,
                    status=status,
                    auto_status=status,
                    detection_row_id=detection.id if detection else None,
                    similarity=similarity,
                )
            )
        db.flush()
        db.refresh(session)

    @staticmethod
    def sync_roster(db: Session, session_id: str) -> AttendanceSession:
        """Ensure a session under review has a proposed row for each active student.

        Covers sessions processed before proposed attendance existed and
        students added to the roster after the image was processed.
        """
        session = AttendanceService._get(db, session_id)
        if session.status != "review_required":
            return session
        existing = {row.student_id for row in session.proposed_attendance}
        roster = {
            student.id for student in AttendanceService.roster_students(db, session.class_section)
        }
        if roster - existing:
            AttendanceService._build_proposed_attendance(db, session)
            db.commit()
            db.refresh(session)
        return session

    # ----------------------------------------------------------------- review

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
        """Resolve one detected face: assign it to a student, or reject it."""
        session = AttendanceService.sync_roster(db, session_id)
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
        if present:
            AttendanceService._require_active_student(db, student_id, session.class_section)
            other = db.execute(
                select(AttendanceDetection.detection_id)
                .join(ProposedMatch, ProposedMatch.detection_row_id == AttendanceDetection.id)
                .where(
                    AttendanceDetection.session_id == session_id,
                    AttendanceDetection.id != detection.id,
                    AttendanceDetection.photo_index == detection.photo_index,
                    ProposedMatch.student_id == student_id,
                )
            ).scalars().first()
            if other is not None:
                raise ValidationError(
                    f"This student is already assigned to face '{other}' in the same photo. "
                    "Unassign that face first so one student is never counted twice."
                )

        match = detection.proposed_match
        previous_student_id = match.student_id
        db.add(
            ReviewDecision(
                session_id=session.id,
                detection_row_id=detection.id,
                reviewer=actor,
                decision="present" if present else "absent",
                original_student_id=previous_student_id,
                selected_student_id=student_id if present else None,
                notes=notes,
            )
        )
        match.student_id = student_id if present else None
        match.reviewed = True
        match.status = "reviewed_present" if present else "reviewed_absent"
        match.rejection_reason = notes if not present else None

        rows = {row.student_id: row for row in session.proposed_attendance}
        now = _now()
        # Any student previously linked to this face loses that evidence.
        for row in rows.values():
            if row.detection_row_id == detection.id and row.student_id != (student_id if present else None):
                # The same student may still be identified in another photo.
                fallback = next(
                    (
                        other
                        for other in session.detections
                        if other.id != detection.id
                        and other.proposed_match
                        and other.proposed_match.student_id == row.student_id
                    ),
                    None,
                )
                row.detection_row_id = fallback.id if fallback else None
                row.similarity = fallback.proposed_match.similarity if fallback else None
                if fallback is None and row.status in {PROPOSED_PRESENT, PROPOSED_NEEDS_REVIEW}:
                    row.status = PROPOSED_NOT_DETECTED
                row.manually_set = True
                row.updated_by, row.updated_at = actor, now
                row.notes = notes or f"Face {detection_id} reassigned during review"
        if present:
            row = rows.get(student_id)
            if row is None:
                row = ProposedAttendance(
                    session_id=session.id,
                    student_id=student_id,
                    auto_status=PROPOSED_NOT_DETECTED,
                    status=PROPOSED_NOT_DETECTED,
                )
                db.add(row)
            unchanged = row.status == PROPOSED_PRESENT and row.detection_row_id == detection.id
            row.status = PROPOSED_PRESENT
            row.detection_row_id = detection.id
            row.similarity = match.similarity
            if not unchanged:
                row.manually_set = True
            row.updated_by, row.updated_at = actor, now
            if notes:
                row.notes = notes
        AttendanceService._audit(db, "DETECTION_REVIEWED", session.id, actor, detection_id)
        db.commit()
        return match

    @staticmethod
    def set_student_attendance(
        db: Session,
        session_id: str,
        student_id: str,
        status: str,
        actor: str = "system",
        notes: Optional[str] = None,
    ) -> ProposedAttendance:
        """Manually mark one roster student PRESENT or ABSENT before confirmation."""
        if status not in {PROPOSED_PRESENT, PROPOSED_ABSENT}:
            raise ValidationError("Attendance can be set manually only to 'present' or 'absent'")
        if not actor or not actor.strip():
            raise ValidationError("A manual attendance change requires a reviewer identity")
        session = AttendanceService.sync_roster(db, session_id)
        AttendanceService._require_status(session, {"review_required"})
        row = next((r for r in session.proposed_attendance if r.student_id == student_id), None)
        if row is None:
            raise ResourceNotFoundError("Roster student in this session", student_id)
        now = _now()
        released = [
            detection
            for detection in session.detections
            if detection.proposed_match and detection.proposed_match.student_id == student_id
        ] if status == PROPOSED_ABSENT else []
        if status == PROPOSED_ABSENT and (row.detection_row_id or released):
            # The reviewer is overriding a face identification; release every
            # face (in any photo) attached to this student so they show as
            # unresolved rather than silently keeping the wrong identity.
            for detection in released:
                match = detection.proposed_match
                db.add(
                    ReviewDecision(
                        session_id=session.id,
                        detection_row_id=detection.id,
                        reviewer=actor,
                        decision="absent",
                        original_student_id=student_id,
                        selected_student_id=None,
                        notes=notes or "Student marked absent; face identification rejected",
                    )
                )
                match.student_id = None
                match.reviewed = True
                match.status = "reviewed_absent"
                match.rejection_reason = notes or "Identity rejected by reviewer"
            row.detection_row_id = None
            row.similarity = None
        if row.status != status:
            row.manually_set = True
        row.status = status
        row.updated_by, row.updated_at = actor, now
        if notes is not None:
            row.notes = notes
        AttendanceService._audit(
            db, "PROPOSED_ATTENDANCE_UPDATED", session.id, actor, f"{student_id}:{status}"
        )
        db.commit()
        db.refresh(row)
        return row

    # ----------------------------------------------------------- confirmation

    @staticmethod
    def validate_for_confirmation(db: Session, session: AttendanceSession) -> list[str]:
        """Return blocking problems; an empty list means the session can be confirmed."""
        problems: list[str] = []
        rows = session.proposed_attendance
        if not rows:
            problems.append("No active students are on the roster for this session.")
        counts = Counter(row.student_id for row in rows)
        for student_id, count in counts.items():
            if count > 1:
                problems.append(f"Student '{student_id}' has {count} proposed entries.")
        students = {
            s.id: s
            for s in db.execute(select(Student).where(Student.id.in_(list(counts)))).scalars()
        } if counts else {}
        for row in rows:
            student = students.get(row.student_id)
            if student is None:
                problems.append(f"Proposed entry references unknown student '{row.student_id}'.")
            if row.status not in {
                PROPOSED_PRESENT, PROPOSED_ABSENT, PROPOSED_NEEDS_REVIEW, PROPOSED_NOT_DETECTED
            }:
                problems.append(f"Invalid proposed status '{row.status}'.")
        face_owners = Counter(
            row.detection_row_id for row in rows if row.status == PROPOSED_PRESENT and row.detection_row_id
        )
        for detection_row_id, count in face_owners.items():
            if count > 1:
                problems.append("One detected face is assigned to more than one present student.")
        # A student may appear in several photos, but only once per photo.
        assigned = Counter(
            (d.photo_index or 1, d.proposed_match.student_id)
            for d in session.detections
            if d.proposed_match and d.proposed_match.student_id
        )
        photo_of = {d.id: d.photo_index or 1 for d in session.detections}
        rows_by_student = {row.student_id: row for row in rows}
        for detection in session.detections:
            match = detection.proposed_match
            if not match or not match.student_id:
                continue
            count = assigned[(detection.photo_index or 1, match.student_id)]
            if count > 1:
                problems.append(
                    f"Student '{match.student_id}' is assigned to {count} faces in one photo."
                )
                continue
            row = rows_by_student.get(match.student_id)
            if (
                row is not None
                and row.status == PROPOSED_PRESENT
                and row.detection_row_id not in (None, detection.id)
                and photo_of.get(row.detection_row_id) == (detection.photo_index or 1)
            ):
                problems.append(
                    f"Face '{detection.detection_id}' and the roster disagree about who it is."
                )
        return sorted(set(problems))

    @staticmethod
    def confirm(db: Session, session_id: str, actor: str = "system") -> AttendanceSession:
        """Persist final attendance in one transaction. Idempotent once confirmed."""
        if not actor or not actor.strip():
            raise ValidationError("Confirmation requires a reviewer identity")
        session = AttendanceService._get(db, session_id)
        if session.status == "confirmed":
            return session
        AttendanceService._require_status(session, {"review_required"})
        session = AttendanceService.sync_roster(db, session_id)
        problems = AttendanceService.validate_for_confirmation(db, session)
        if problems:
            raise ValidationError(
                "Attendance cannot be confirmed: " + " ".join(problems),
                details={"problems": problems},
            )

        confirmed_at = _now()
        try:
            for record in list(session.attendance):
                db.delete(record)
            db.flush()
            for row in session.proposed_attendance:
                if row.status == PROPOSED_PRESENT:
                    final_status = FINAL_PRESENT
                    if row.detection_row_id and not row.manually_set:
                        method = VERIFIED_BY_RECOGNITION
                    elif row.detection_row_id:
                        method = VERIFIED_BY_FACE_REVIEW
                    else:
                        method = VERIFIED_MANUALLY
                elif row.status == PROPOSED_ABSENT:
                    final_status, method = FINAL_ABSENT, VERIFIED_MANUALLY
                else:
                    # NOT_DETECTED / NEEDS_REVIEW are never silently turned into absences.
                    final_status, method = FINAL_UNVERIFIED, VERIFIED_UNRESOLVED
                db.add(
                    AttendanceRecord(
                        session_id=session.id,
                        student_id=row.student_id,
                        present=final_status == FINAL_PRESENT,
                        attendance_status=final_status,
                        source="auto" if method == VERIFIED_BY_RECOGNITION else "review",
                        detection_row_id=row.detection_row_id,
                        verification_method=method,
                        confirmed_at=confirmed_at,
                        reviewed_by=actor,
                    )
                )
            session.status = "confirmed"
            session.confirmed_at = confirmed_at
            session.confirmed_by = actor
            AttendanceService._audit(db, "SESSION_CONFIRMED", session.id, actor)
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            # A concurrent request may have confirmed the session first.
            db.expire_all()
            current = db.get(AttendanceSession, session_id)
            if current is not None and current.status == "confirmed":
                return current
            raise DatabaseError(
                "Attendance could not be saved. No records were changed; please retry.",
                details={"reason": exc.__class__.__name__},
            ) from exc
        db.refresh(session)
        return session

    # ------------------------------------------------------------- correction

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
        records = {
            record.student_id: record
            for record in db.execute(
                select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
            ).scalars()
        }
        target = None
        if present:
            AttendanceService._require_active_student(db, student_id, session.class_section)
            target = records.get(student_id)
            if (
                target is not None
                and target.attendance_status == FINAL_PRESENT
                and student_id != match.student_id
            ):
                raise ValidationError(f"Student '{student_id}' is already present in this session")

        now = _now()
        try:
            original_student_id = match.student_id
            if original_student_id and original_student_id != (student_id if present else None):
                old_record = records.get(original_student_id)
                if old_record is not None:
                    old_record.attendance_status = FINAL_UNVERIFIED
                    old_record.present = False
                    old_record.detection_row_id = None
                    old_record.verification_method = VERIFIED_BY_CORRECTION
                    old_record.corrected_at, old_record.corrected_by = now, actor
                    old_record.correction_reason = reason

            if present:
                if target is None:
                    target = AttendanceRecord(
                        session_id=session.id,
                        student_id=student_id,
                        present=True,
                        confirmed_at=session.confirmed_at,
                        reviewed_by=session.confirmed_by,
                    )
                    db.add(target)
                target.attendance_status = FINAL_PRESENT
                target.present = True
                target.source = "correction"
                target.detection_row_id = detection.id
                target.verification_method = VERIFIED_BY_CORRECTION
                target.corrected_at, target.corrected_by = now, actor
                target.correction_reason = reason

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
        except SQLAlchemyError:
            db.rollback()
            raise

        db.refresh(session)
        return session

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def proposal_summary(session: AttendanceSession) -> dict[str, int]:
        rows = session.proposed_attendance
        unknown_faces = sum(
            1
            for d in session.detections
            if d.proposed_match
            and not d.proposed_match.student_id
            and d.proposed_match.status not in _REJECTED_FACE_STATUSES
        )
        return {
            "total_registered": len(rows),
            "auto_identified": sum(1 for r in rows if r.auto_status == PROPOSED_PRESENT),
            "proposed_present": sum(1 for r in rows if r.status == PROPOSED_PRESENT),
            "proposed_absent": sum(1 for r in rows if r.status == PROPOSED_ABSENT),
            "needs_review": sum(1 for r in rows if r.status == PROPOSED_NEEDS_REVIEW),
            "not_detected": sum(1 for r in rows if r.status == PROPOSED_NOT_DETECTED),
            "unknown_faces": unknown_faces,
            "faces_detected": len(session.detections),
            "manually_corrected": sum(1 for r in rows if r.manually_set),
        }

    @staticmethod
    def final_summary(session: AttendanceSession) -> dict[str, int]:
        records = session.attendance
        return {
            "total_registered": len(records),
            "present": sum(1 for r in records if r.attendance_status == FINAL_PRESENT),
            "absent": sum(1 for r in records if r.attendance_status == FINAL_ABSENT),
            "unverified": sum(1 for r in records if r.attendance_status == FINAL_UNVERIFIED),
            "auto_identified": sum(
                1 for r in records if r.verification_method == VERIFIED_BY_RECOGNITION
            ),
            "manually_corrected": sum(
                1
                for r in records
                if r.verification_method
                in {VERIFIED_BY_FACE_REVIEW, VERIFIED_MANUALLY, VERIFIED_BY_CORRECTION}
                and r.attendance_status != FINAL_UNVERIFIED
            ),
            "faces_detected": len(session.detections),
        }

    @staticmethod
    def _require_active_student(
        db: Session, student_id: str, class_section: Optional[str] = None
    ) -> Student:
        student = db.get(Student, student_id)
        if student is None:
            raise ResourceNotFoundError("Student", student_id)
        if not student.is_active:
            raise ValidationError(f"Student '{student.student_id}' is not on the active roster")
        if class_section and student.class_section != class_section:
            raise ValidationError(
                f"Student '{student.student_id}' is not in class {class_section} for this session"
            )
        return student

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
    def _audit(
        db: Session, action: str, entity_id: str, actor: str, details: Optional[str] = None
    ) -> None:
        db.add(
            AuditEvent(
                action=action,
                entity_type="attendance_session",
                entity_id=entity_id,
                actor=actor,
                details=details,
            )
        )
