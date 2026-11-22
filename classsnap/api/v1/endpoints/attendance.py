"""Attendance session lifecycle endpoints."""

import json
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from classsnap.db.session import get_db
from classsnap.schemas.attendance import (
    AttendanceConfirmRequest,
    AttendanceCorrectionRequest,
    AttendanceDetectionResponse,
    AttendanceProposalRequest,
    AttendanceReviewRequest,
    AttendanceReviewResponse,
    AttendanceSessionCreate,
    AttendanceSessionDetailResponse,
    AttendanceSessionResponse,
    RosterAttendanceEntry,
    SessionHistoryItem,
    StudentAttendanceHistory,
    StudentAttendanceUpdate,
)
from classsnap.services.attendance_service import AttendanceService
from classsnap.services.report_service import ReportService
from classsnap.schemas.report import AttendanceReportSummary
from classsnap.models.student import Student

router = APIRouter(prefix="/attendance/sessions", tags=["Attendance"])
students_router = APIRouter(prefix="/attendance/students", tags=["Attendance"])


def _iso(value) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _session_response(session) -> AttendanceSessionResponse:
    confirmed_at = session.confirmed_at.isoformat() if isinstance(session.confirmed_at, datetime) else None
    class_at = session.class_at.isoformat() if isinstance(session.class_at, datetime) else None
    return AttendanceSessionResponse(
        id=session.id,
        name=session.name,
        status=session.status,
        created_by=session.created_by,
        class_at=class_at,
        class_section=session.class_section,
        confirmed_at=confirmed_at,
        confirmed_by=session.confirmed_by,
    )


def _preview_url(session, detection) -> str | None:
    if detection is None or not detection.preview_blob:
        return None
    return f"/api/v1/attendance/sessions/{session.id}/detections/{detection.detection_id}/preview"


def _session_detail_response(session, db: Session) -> AttendanceSessionDetailResponse:
    """Full session state. The backend is the single source of attendance truth."""
    if session.status == "review_required":
        session = AttendanceService.sync_roster(db, session.id)
    detections_by_row = {d.id: d for d in session.detections}
    student_ids = {
        sid
        for d in session.detections
        if d.proposed_match
        for sid in (d.proposed_match.student_id, d.proposed_match.candidate_student_id)
        if sid
    }
    student_ids |= {row.student_id for row in session.proposed_attendance}
    student_ids |= {record.student_id for record in session.attendance}
    students = {
        student.id: student
        for student in db.execute(select(Student).where(Student.id.in_(student_ids))).scalars()
    } if student_ids else {}

    def recognition_status(auto_status, detection_row_id, manually_set):
        if auto_status == "present":
            return "matched"
        if auto_status == "needs_review":
            return "ambiguous"
        if detection_row_id and manually_set:
            return "manual"
        return "not_detected"

    entries: list[RosterAttendanceEntry] = []
    if session.status == "confirmed" and session.attendance:
        proposed = {row.student_id: row for row in session.proposed_attendance}
        for record in session.attendance:
            student = students.get(record.student_id)
            row = proposed.get(record.student_id)
            detection = detections_by_row.get(record.detection_row_id)
            entries.append(
                RosterAttendanceEntry(
                    student_id=record.student_id,
                    student_usn=student.student_id if student else "",
                    student_name=student.full_name if student else "Removed student",
                    status=record.attendance_status,
                    auto_status=row.auto_status if row else None,
                    recognition_status=(
                        recognition_status(row.auto_status, row.detection_row_id, row.manually_set)
                        if row
                        else ("matched" if detection else "not_detected")
                    ),
                    detection_id=detection.detection_id if detection else None,
                    similarity=(
                        detection.proposed_match.similarity
                        if detection and detection.proposed_match
                        else None
                    ),
                    preview_url=_preview_url(session, detection),
                    manually_set=bool(row.manually_set) if row else False,
                    notes=row.notes if row else None,
                    attendance_id=record.id,
                    verification_method=record.verification_method,
                    reviewed_by=record.reviewed_by,
                    confirmed_at=_iso(record.confirmed_at),
                    corrected_by=record.corrected_by,
                    correction_reason=record.correction_reason,
                )
            )
        summary = AttendanceService.final_summary(session)
        problems: list[str] = []
    else:
        for row in session.proposed_attendance:
            student = students.get(row.student_id)
            detection = detections_by_row.get(row.detection_row_id)
            entries.append(
                RosterAttendanceEntry(
                    student_id=row.student_id,
                    student_usn=student.student_id if student else "",
                    student_name=student.full_name if student else "Removed student",
                    status=row.status,
                    auto_status=row.auto_status,
                    recognition_status=recognition_status(
                        row.auto_status, row.detection_row_id, row.manually_set
                    ),
                    detection_id=detection.detection_id if detection else None,
                    similarity=row.similarity,
                    preview_url=_preview_url(session, detection),
                    manually_set=row.manually_set,
                    updated_by=row.updated_by,
                    updated_at=_iso(row.updated_at),
                    notes=row.notes,
                )
            )
        summary = AttendanceService.proposal_summary(session)
        problems = (
            AttendanceService.validate_for_confirmation(db, session)
            if session.status == "review_required"
            else []
        )
    entries.sort(key=lambda e: e.student_usn)

    def bbox(detection):
        try:
            return json.loads(detection.bbox_json) if detection.bbox_json else None
        except ValueError:
            return None

    return AttendanceSessionDetailResponse(
        **_session_response(session).model_dump(),
        detections=[
            AttendanceDetectionResponse(
                detection_id=detection.detection_id,
                status=detection.proposed_match.status if detection.proposed_match else detection.status,
                student_id=detection.proposed_match.student_id if detection.proposed_match else None,
                student_name=(
                    students[detection.proposed_match.student_id].full_name
                    if detection.proposed_match
                    and detection.proposed_match.student_id in students
                    else None
                ),
                student_usn=(
                    students[detection.proposed_match.student_id].student_id
                    if detection.proposed_match
                    and detection.proposed_match.student_id in students
                    else None
                ),
                similarity=detection.proposed_match.similarity if detection.proposed_match else None,
                rejection_reason=detection.proposed_match.rejection_reason if detection.proposed_match else None,
                reviewed=detection.proposed_match.reviewed if detection.proposed_match else False,
                preview_url=_preview_url(session, detection),
                bbox=bbox(detection),
                candidate_student_id=(
                    detection.proposed_match.candidate_student_id if detection.proposed_match else None
                ),
                candidate_student_name=(
                    students[detection.proposed_match.candidate_student_id].full_name
                    if detection.proposed_match
                    and detection.proposed_match.candidate_student_id in students
                    else None
                ),
            )
            for detection in session.detections
        ],
        attendance=entries,
        summary=summary,
        confirmation_problems=problems,
    )


@router.post("", response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: AttendanceSessionCreate, db: Session = Depends(get_db)):
    return _session_response(
        AttendanceService.create_session(
            db, payload.name, payload.actor, payload.class_at, payload.class_section
        )
    )


@router.get("", response_model=list[SessionHistoryItem])
def list_sessions(
    session_status: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """Attendance history: every session with its confirmed counts."""
    return ReportService.session_history(db, session_status)


@router.get("/{session_id}", response_model=AttendanceSessionDetailResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    return _session_detail_response(AttendanceService.get_session(db, session_id), db)


@router.get("/{session_id}/detections/{detection_id}/preview")
def detection_preview(session_id: str, detection_id: str, db: Session = Depends(get_db)):
    detection = AttendanceService.get_detection(db, session_id, detection_id)
    if detection.preview_blob is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        content=detection.preview_blob,
        media_type=detection.preview_mime_type or "image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.get("/{session_id}/report")
def export_report(
    session_id: str,
    file_format: str = Query("csv", alias="format", pattern="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
):
    content, media_type, filename = ReportService.export_attendance(db, session_id, file_format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/summary", response_model=AttendanceReportSummary)
def report_summary(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    return ReportService.confirmed_sessions(db, date_from, date_to)


@router.post("/{session_id}/process", response_model=AttendanceSessionResponse)
def begin_processing(session_id: str, db: Session = Depends(get_db)):
    return _session_response(AttendanceService.begin_processing(db, session_id))


@router.post("/{session_id}/proposals", response_model=AttendanceSessionResponse)
def add_proposals(
    session_id: str, payload: AttendanceProposalRequest, db: Session = Depends(get_db)
):
    proposals = [
        (
            proposal.detection_id,
            proposal.status,
            proposal.student_id,
            proposal.similarity,
            proposal.rejection_reason,
        )
        for proposal in payload.proposals
    ]
    return _session_response(
        AttendanceService.add_proposals(db, session_id, proposals, payload.actor)
    )


@router.post(
    "/{session_id}/detections/{detection_id}/review",
    response_model=AttendanceReviewResponse,
)
def review_detection(
    session_id: str,
    detection_id: str,
    payload: AttendanceReviewRequest,
    db: Session = Depends(get_db),
):
    match = AttendanceService.review_detection(
        db,
        session_id,
        detection_id,
        payload.student_id,
        payload.present,
        payload.actor,
        payload.notes,
    )
    return AttendanceReviewResponse(
        id=match.id,
        status=match.status,
        student_id=match.student_id,
        reviewed=match.reviewed,
    )


@router.put(
    "/{session_id}/attendance/{student_id}",
    response_model=AttendanceSessionDetailResponse,
)
def set_student_attendance(
    session_id: str,
    student_id: str,
    payload: StudentAttendanceUpdate,
    db: Session = Depends(get_db),
):
    """Manually mark one roster student present or absent before confirmation."""
    AttendanceService.set_student_attendance(
        db, session_id, student_id, payload.status, payload.actor, payload.notes
    )
    return _session_detail_response(AttendanceService.get_session(db, session_id), db)


@router.post("/{session_id}/confirm", response_model=AttendanceSessionDetailResponse)
def confirm_session(
    session_id: str,
    actor: str = "system",
    payload: AttendanceConfirmRequest | None = Body(None),
    db: Session = Depends(get_db),
):
    """Persist final attendance in one transaction. Repeat calls are idempotent."""
    reviewer = payload.actor if payload else actor
    session = AttendanceService.confirm(db, session_id, reviewer)
    return _session_detail_response(session, db)


@router.post("/{session_id}/detections/{detection_id}/correction", response_model=AttendanceSessionResponse)
def correct_attendance(
    session_id: str,
    detection_id: str,
    payload: AttendanceCorrectionRequest,
    db: Session = Depends(get_db),
):
    return _session_response(
        AttendanceService.correct_confirmed_attendance(
            db,
            session_id,
            detection_id,
            payload.student_id,
            payload.present,
            payload.actor,
            payload.reason,
        )
    )


@students_router.get("/{student_ref}/history", response_model=StudentAttendanceHistory)
def student_history(student_ref: str, db: Session = Depends(get_db)):
    """Confirmed attendance history for one student (internal id or USN)."""
    return ReportService.student_history(db, student_ref)
