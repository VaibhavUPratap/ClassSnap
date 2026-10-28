"""Classroom image processing endpoint."""

import numpy as np
import cv2
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
from classsnap.cv.deduplication import non_maximum_suppression

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

    image_bytes = await read_image_upload(image)
    detections, _ = cv_engine.process_image(
        image_bytes,
        score_threshold=0.40,
        extract_embeddings=True,
        use_tiling=False,
    )
    detections = non_maximum_suppression(detections)
    matcher = MatchingService()
    # Keep one crop for overlapping boxes of the same physical face. For
    # oversized portraits, the strongest detector box is not always the best
    # aligned crop, so choose the crop with the strongest roster similarity.
    groups = []
    for candidate in detections:
        candidate_center = (
            candidate.bbox.x + candidate.bbox.w / 2,
            candidate.bbox.y + candidate.bbox.h / 2,
        )
        group = next(
            (
                group
                for group in groups
                if np.hypot(
                    candidate_center[0] - group["center"][0],
                    candidate_center[1] - group["center"][1],
                )
                <= 0.70
                * min(
                    candidate.bbox.w,
                    candidate.bbox.h,
                    group["detection"].bbox.w,
                    group["detection"].bbox.h,
                )
            ),
            None,
        )
        if group is None:
            groups.append({"center": candidate_center, "detection": candidate})
            continue
        current = group["detection"]
        current_match = matcher.match_single(
            current.detection_id,
            np.asarray(current.embedding, dtype=np.float32)
            if current.embedding is not None
            else None,
            roster_embeddings,
            model_version,
        )
        candidate_match = matcher.match_single(
            candidate.detection_id,
            np.asarray(candidate.embedding, dtype=np.float32)
            if candidate.embedding is not None
            else None,
            roster_embeddings,
            model_version,
        )
        current_score = (
            current_match.top_candidate.similarity
            if current_match.top_candidate
            else -1.0
        )
        candidate_score = (
            candidate_match.top_candidate.similarity
            if candidate_match.top_candidate
            else -1.0
        )
        if candidate_score > current_score:
            group["detection"] = candidate
    detections = [group["detection"] for group in groups]
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
    source_image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if source_image is not None:
        detections_by_id = {detection.detection_id: detection for detection in detections}
        for detection in session.detections:
            source_detection = detections_by_id.get(detection.detection_id)
            if source_detection is None:
                continue
            aligned = cv_engine.aligner.align(source_image, source_detection)
            encoded, preview = cv2.imencode(
                ".jpg", aligned, [cv2.IMWRITE_JPEG_QUALITY, 82]
            )
            if encoded:
                detection.preview_blob = preview.tobytes()
                detection.preview_mime_type = "image/jpeg"
    db.commit()
    db.refresh(session)
    return _session_response(session)
