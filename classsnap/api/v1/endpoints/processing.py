"""Classroom image processing endpoint."""

import dataclasses
import json

import numpy as np
import cv2
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from classsnap.db.session import get_db
from classsnap.models.student import Student
from classsnap.schemas.attendance import AttendanceSessionDetailResponse
from classsnap.exceptions import ValidationError
from classsnap.services.attendance_service import MAX_PHOTOS_PER_SESSION, AttendanceService
from classsnap.services.enrollment_service import EnrollmentService
from classsnap.services.matching_service import MatchingService
from classsnap.services.matching_service import STATUS_AMBIGUOUS, STATUS_MATCHED
from classsnap.cv.engine import CVEngine
from classsnap.cv.geometry import compute_iou
from classsnap.cv.deduplication import non_maximum_suppression

from classsnap.api.v1.endpoints.attendance import _session_detail_response
from classsnap.api.v1.upload import read_image_upload

router = APIRouter(prefix="/attendance/sessions", tags=["Attendance"])


MAX_PHOTOS_PER_REQUEST = MAX_PHOTOS_PER_SESSION


def _roster_embeddings(db: Session, session, cv_engine):
    """Embeddings for the session's roster. Only the session's class is
    matched, so students of other classes can never be proposed present."""
    model_version = cv_engine.embedder.model_version
    roster_embeddings = {}
    for student in AttendanceService.roster_students(db, session.class_section):
        embedding = EnrollmentService.get_aggregated_student_embedding(
            db, student.id, required_model_version=model_version
        )
        if embedding is not None:
            roster_embeddings[student.id] = (student.full_name, embedding, model_version)
    return roster_embeddings, model_version


@router.post("/{session_id}/image", response_model=AttendanceSessionDetailResponse)
async def process_classroom_image(
    session_id: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Detect, embed, match, and persist proposals for one classroom photo.

    The response carries the proposed roster: confidently and uniquely matched
    students are already PRESENT; nothing is final until confirmation. Calling
    it again before confirmation adds another photo to the same session.
    """
    return await process_classroom_images(session_id, [image], db)


@router.post("/{session_id}/images", response_model=AttendanceSessionDetailResponse)
async def process_classroom_images(
    session_id: str,
    images: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Process one or more classroom photos of the same class into one session.

    A student recognised in any photo is proposed PRESENT once. Every upload is
    validated before any face detection runs.
    """
    if not images:
        raise ValidationError("Choose at least one classroom photo.")
    if len(images) > MAX_PHOTOS_PER_REQUEST:
        raise ValidationError(f"Upload at most {MAX_PHOTOS_PER_REQUEST} photos at a time.")
    # Fail fast (before running the CV pipeline) on closed sessions or too many photos.
    session = AttendanceService.require_image_upload_allowed(db, session_id, len(images))
    photos = [await read_image_upload(image) for image in images]
    cv_engine = CVEngine.from_settings()
    roster_embeddings, model_version = _roster_embeddings(db, session, cv_engine)
    for image_bytes in photos:
        _process_photo(db, session_id, cv_engine, roster_embeddings, model_version, image_bytes)
    session = AttendanceService.get_session(db, session_id)
    db.refresh(session)
    return _session_detail_response(session, db)


def _process_photo(db: Session, session_id: str, cv_engine, roster_embeddings, model_version, image_bytes):
    """Detect and match the faces of one photo and store them as its proposals."""
    detections, _ = cv_engine.process_image(
        image_bytes,
        score_threshold=0.65,
        extract_embeddings=True,
        use_tiling=True,
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
    # Keep face IDs unique across the photos of one session.
    photo_index = AttendanceService.photo_count(AttendanceService.get_session(db, session_id)) + 1
    if photo_index > 1:
        detections = [
            dataclasses.replace(detection, detection_id=f"p{photo_index}-{detection.detection_id}")
            for detection in detections
        ]
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
            result.top_candidate.student_id if result.status == STATUS_MATCHED else None,
            result.top_candidate.similarity if result.top_candidate else None,
            result.rejection_reason,
            # Ambiguous faces only *flag* their best candidate for manual
            # verification; they are never auto-marked present.
            result.top_candidate.student_id
            if result.status == STATUS_AMBIGUOUS and result.top_candidate
            else None,
        )
        for result in matches
        if result.detection_id not in suppressed_unknowns
    ]
    session = AttendanceService.add_proposals(db, session_id, proposals)
    try:
        source_image = cv_engine.load_image(image_bytes)
    except Exception:
        source_image = None
    detections_by_id = {detection.detection_id: detection for detection in detections}
    image_height, image_width = (
        source_image.shape[:2] if source_image is not None else (None, None)
    )
    for detection in session.detections:
        if detection.photo_index != session.photo_count:
            continue
        source_detection = detections_by_id.get(detection.detection_id)
        if source_detection is None:
            continue
        box = source_detection.bbox
        detection.bbox_json = json.dumps(
            {
                "x": float(box.x),
                "y": float(box.y),
                "w": float(box.w),
                "h": float(box.h),
                "image_width": image_width,
                "image_height": image_height,
            }
        )
        if source_image is not None:
            align = getattr(cv_engine, "align_for_recognition", cv_engine.aligner.align)
            aligned = align(source_image, source_detection)
            encoded, preview = cv2.imencode(
                ".jpg", aligned, [cv2.IMWRITE_JPEG_QUALITY, 82]
            )
            if encoded:
                detection.preview_blob = preview.tobytes()
                detection.preview_mime_type = "image/jpeg"
    db.commit()
