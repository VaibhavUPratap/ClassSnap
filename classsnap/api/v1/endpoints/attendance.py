"""Attendance session lifecycle endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from classsnap.db.session import get_db
from classsnap.schemas.attendance import (
    AttendanceCorrectionRequest,
    AttendanceDetectionResponse,
    AttendanceProposalRequest,
    AttendanceReviewRequest,
    AttendanceReviewResponse,
    AttendanceSessionCreate,
    AttendanceSessionDetailResponse,
    AttendanceSessionResponse,
)
from classsnap.services.attendance_service import AttendanceService
from classsnap.services.report_service import ReportService
from classsnap.schemas.report import AttendanceReportSummary

router = APIRouter(prefix="/attendance/sessions", tags=["Attendance"])


def _session_response(session) -> AttendanceSessionResponse:
    confirmed_at = session.confirmed_at.isoformat() if isinstance(session.confirmed_at, datetime) else None
    class_at = session.class_at.isoformat() if isinstance(session.class_at, datetime) else None
    return AttendanceSessionResponse(
        id=session.id,
        name=session.name,
        status=session.status,
        created_by=session.created_by,
        class_at=class_at,
        confirmed_at=confirmed_at,
    )


def _session_detail_response(session) -> AttendanceSessionDetailResponse:
    return AttendanceSessionDetailResponse(
        **_session_response(session).model_dump(),
        detections=[
            AttendanceDetectionResponse(
                detection_id=detection.detection_id,
                status=detection.proposed_match.status if detection.proposed_match else detection.status,
                student_id=detection.proposed_match.student_id if detection.proposed_match else None,
                similarity=detection.proposed_match.similarity if detection.proposed_match else None,
                rejection_reason=detection.proposed_match.rejection_reason if detection.proposed_match else None,
                reviewed=detection.proposed_match.reviewed if detection.proposed_match else False,
            )
            for detection in session.detections
        ],
    )


@router.post("", response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: AttendanceSessionCreate, db: Session = Depends(get_db)):
    return _session_response(
        AttendanceService.create_session(db, payload.name, payload.actor, payload.class_at)
    )


@router.get("/{session_id}", response_model=AttendanceSessionDetailResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    return _session_detail_response(AttendanceService.get_session(db, session_id))


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


@router.post("/{session_id}/confirm", response_model=AttendanceSessionResponse)
def confirm_session(session_id: str, actor: str = "system", db: Session = Depends(get_db)):
    return _session_response(AttendanceService.confirm(db, session_id, actor))


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
