"""Classroom image processing endpoint."""

import numpy as np
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from classsnap.db.session import get_db
from classsnap.models.student import Student
from classsnap.schemas.attendance import AttendanceSessionResponse
from classsnap.services.attendance_service import AttendanceService
from classsnap.services.enrollment_service import EnrollmentService
from classsnap.services.matching_service import MatchingService
from classsnap.services.matching_service import STATUS_AMBIGUOUS, STATUS_MATCHED
from classsnap.cv.engine import CVEngine
from classsnap.cv.geometry import compute_iou

from classsnap.api.v1.endpoints.attendance import _session_response
from classsnap.api.v1.upload import read_image_upload

router = APIRouter(prefix="/attendance/sessions", tags=["Attendance"])


@router.post("/{session_id}/image", response_model=AttendanceSessionResponse)
async def process_classroom_image(
    session_id: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Detect, embed, match, and persist proposals for one classroom image."""
    cv_engine = CVEngine.from_settings()
    model_version = cv_engine.embedder.model_version
    roster_embeddings = {}
    students = db.execute(select(Student).where(Student.is_active == True)).scalars().all()
    for student in students:
        embedding = EnrollmentService.get_aggregated_student_embedding(
            db, student.id, required_model_version=model_version
        )
        if embedding is not None:
            roster_embeddings[student.id] = (student.full_name, embedding, model_version)

    detections, _ = cv_engine.process_image(
        await read_image_upload(image),
        score_threshold=0.40,
        extract_embeddings=True,
        use_tiling=False,
    )
    matcher = MatchingService()
    detection_inputs = [
        (
            detection.detection_id,
            np.asarray(detection.embedding, dtype=np.float32)
            if detection.embedding is not None
            else None,
            "usable" if detection.quality.is_usable else "low_quality",
        )
        for detection in detections
    ]
    matches = matcher.match_all(detection_inputs, roster_embeddings, model_version)
    positive_detections = {
        result.detection_id
        for result in matches
        if result.status in {STATUS_MATCHED, STATUS_AMBIGUOUS}
        and result.top_candidate is not None
        and result.top_candidate.similarity >= matcher.thresholds.accept
    }
    detection_by_id = {detection.detection_id: detection for detection in detections}
    suppressed_unknowns = {
        result.detection_id
        for result in matches
        if result.detection_id not in positive_detections
        and any(
            compute_iou(
                detection_by_id[result.detection_id].bbox,
                detection_by_id[positive_id].bbox,
            ) >= 0.15
            for positive_id in positive_detections
        )
    }
    proposals = [
        (
            result.detection_id,
            result.status,
            result.top_candidate.student_id if result.status == "matched_pending_review" else None,
            result.top_candidate.similarity if result.top_candidate else None,
            result.rejection_reason,
        )
        for result in matches
        if result.detection_id not in suppressed_unknowns
    ]
    session = AttendanceService.add_proposals(db, session_id, proposals)
    return _session_response(session)
