"""
Consent-Based Biometric Face Enrollment Service for ClassSnap.
Handles single-face validation, quality checking, embedding extraction,
multi-reference storage, and aggregated reference vector generation.
"""

import json
import cv2
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Union
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from classsnap.config import get_settings
from classsnap.cv.engine import CVEngine
from classsnap.cv.deduplication import non_maximum_suppression
from classsnap.cv.types import BoundingBox, DetectionResult
from classsnap.exceptions import (
    BiometricProcessingError,
    ResourceNotFoundError,
    ValidationError,
)
from classsnap.logger import get_logger
from classsnap.models.audit import AuditEvent
from classsnap.models.face_template import FaceTemplate
from classsnap.models.student import Student

logger = get_logger("services.enrollment")


class EnrollmentService:
    """Orchestrates consent-governed face reference enrollment and template aggregation."""

    def __init__(self, cv_engine: Optional[CVEngine] = None):
        self.cv_engine = cv_engine or CVEngine.from_settings()

    def _haar_detection_fallback(self, image: np.ndarray) -> List[DetectionResult]:
        """Low-cost Haar cascade fallback for images missed by YuNet."""
        if not hasattr(cv2, "CascadeClassifier"):
            return []
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        boxes = cascade.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=6,
            flags=cv2.CASCADE_SCALE_IMAGE,
            minSize=(40, 40),
            maxSize=(int(image.shape[1] * 0.9), int(image.shape[0] * 0.9)),
        )
        return [
            DetectionResult(
                bbox=BoundingBox(x=int(x), y=int(y), w=int(w), h=int(h)),
                confidence=0.55,
                status="detected",
            )
            for x, y, w, h in boxes
        ]

    # YuNet's anchors target faces far smaller than a full-resolution phone
    # portrait (faces 1000+ px wide). On such images it misses the real face and
    # fires on clothing patterns, so large photos are scanned downscaled first.
    ENROLLMENT_SCAN_SIDES = (1280, 960, 640)

    def _select_enrollment_face(self, image: np.ndarray, student: Student) -> DetectionResult:
        height, width = image.shape[:2]
        longest = max(height, width)
        sides = [side for side in self.ENROLLMENT_SCAN_SIDES if longest > side]
        attempts = ([None] if longest <= self.ENROLLMENT_SCAN_SIDES[0] else []) + sides
        if longest > self.ENROLLMENT_SCAN_SIDES[0]:
            attempts.append(None)  # full resolution as the last resort
        first_error: Optional[BiometricProcessingError] = None
        for side in attempts:
            scale = 1.0 if side is None else side / longest
            working = image if scale == 1.0 else cv2.resize(
                image,
                (max(1, round(width * scale)), max(1, round(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
            try:
                detection = self._select_single_face(working, student)
            except BiometricProcessingError as error:
                first_error = first_error or error
                continue
            return detection if scale == 1.0 else self._rescale_detection(detection, 1.0 / scale)
        raise first_error

    @staticmethod
    def _rescale_detection(detection: DetectionResult, factor: float) -> DetectionResult:
        box = detection.bbox
        detection.bbox = BoundingBox(
            x=int(round(box.x * factor)),
            y=int(round(box.y * factor)),
            w=int(round(box.w * factor)),
            h=int(round(box.h * factor)),
        )
        if detection.landmarks:
            detection.landmarks = [(x * factor, y * factor) for x, y in detection.landmarks]
        return detection

    def _select_single_face(self, image: np.ndarray, student: Student) -> DetectionResult:
        # YuNet, CLAHE-enhanced YuNet, then a Haar fallback.
        detections = self.cv_engine.detector.detect(image, score_threshold=0.40)
        if not any(min(d.bbox.w, d.bbox.h) >= 80 for d in detections):
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            lightness, chroma_a, chroma_b = cv2.split(lab)
            enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lightness)
            enhanced_image = cv2.cvtColor(
                cv2.merge((enhanced, chroma_a, chroma_b)), cv2.COLOR_LAB2BGR
            )
            enhanced_detections = self.cv_engine.detector.detect(
                enhanced_image, score_threshold=0.40
            )
            if enhanced_detections:
                detections = enhanced_detections

        if not detections:
            detections = self._haar_detection_fallback(image)

        if not detections:
            raise BiometricProcessingError(
                message="Enrollment failed: No face was detected in the reference photograph. "
                        "Please provide a well-lit, unobstructed front-facing portrait.",
                details={"student_id": student.student_id, "faces_detected": 0},
            )

        large_detections = [
            detection for detection in detections
            if min(detection.bbox.w, detection.bbox.h) >= 80
        ]
        candidate_detections = non_maximum_suppression(
            large_detections or detections,
            iou_threshold=0.35,
            containment_threshold=0.45,
        )
        if not candidate_detections:
            raise BiometricProcessingError(
                message="Enrollment failed: no sufficiently large face was detected.",
                details={"student_id": student.student_id, "faces_detected": len(detections)},
            )

        if len(candidate_detections) > 1:
            ranked = sorted(
                candidate_detections,
                key=lambda item: (item.bbox.w * item.bbox.h, item.confidence),
                reverse=True,
            )
            dominant = ranked[0]
            second = ranked[1]
            dominant_area = dominant.bbox.w * dominant.bbox.h
            second_area = second.bbox.w * second.bbox.h
            clearly_dominant = (
                dominant.confidence >= 0.65
                and second_area > 0
                and dominant_area / second_area >= 2.0
            )
            if clearly_dominant:
                candidate_detections = [dominant]

        if len(candidate_detections) > 1:
            raise BiometricProcessingError(
                message=f"Enrollment failed: Multiple faces ({len(candidate_detections)}) detected. "
                        "Enrollment photographs must contain exactly one face.",
                details={
                    "student_id": student.student_id,
                    "faces_detected": len(candidate_detections),
                },
            )
        return candidate_detections[0]

    def enroll_student_face(
        self,
        db: Session,
        id_or_student_id: str,
        image_input: Union[str, Path, bytes, np.ndarray],
        consent_granted: Optional[bool] = None,
        consent_notes: Optional[str] = None,
        is_primary: bool = True,
        actor: str = "system",
        retain_original_photo: bool = False,
    ) -> FaceTemplate:
        """
        Enrolls a student's face reference:
        1. Verifies student registration and consent status.
        2. Validates image contains EXACTLY ONE clear, usable face.
        3. Extracts aligned 128D unit-normalized embedding using SFace.
        4. Persists FaceTemplate with model version and quality metrics.
        5. Purges temporary enrollment photo unless retention is authorized.
        """
        # 1. Fetch student
        stmt = select(Student).where(
            (Student.id == id_or_student_id) | (Student.student_id == id_or_student_id)
        )
        student = db.execute(stmt).scalar_one_or_none()
        if not student:
            raise ResourceNotFoundError(resource_type="Student", identifier=id_or_student_id)

        if not student.is_active:
            raise ValidationError(
                f"Cannot enroll inactive student: '{student.student_id}' ({student.full_name})"
            )

        # 2. Verify Consent
        if consent_granted is not None:
            student.has_consent = consent_granted
            if consent_granted:
                student.consent_recorded_at = datetime.now(timezone.utc)
                if consent_notes:
                    student.consent_notes = consent_notes

        if not student.has_consent:
            raise ValidationError(
                message=f"Enrollment rejected: Student '{student.student_id}' does not have verified consent on file.",
                details={"student_id": student.student_id, "has_consent": False},
            )

        # 3. Load and validate image
        image = self.cv_engine.load_image(image_input)

        # 4. Detect exactly one face, retrying at reduced resolution for large photos.
        face_detection = self._select_enrollment_face(image, student)

        # 5. Assess face quality
        quality = self.cv_engine.quality_assessor.assess_quality(image, face_detection)
        if quality.is_usable and 0 < quality.min_dimension < 80:
            raise BiometricProcessingError(
                message=(
                    "Enrollment failed: the detected face is too small "
                    f"({quality.min_dimension}px). Use a clear portrait where the face "
                    "is prominent and not a background graphic."
                ),
                details={
                    "student_id": student.student_id,
                    "min_dimension": quality.min_dimension,
                },
            )
        if not quality.is_usable:
            raise BiometricProcessingError(
                message=f"Enrollment failed: Face quality is insufficient ({quality.rejection_reason}). "
                        f"Please provide a sharper, higher-resolution photograph.",
                details={
                    "student_id": student.student_id,
                    "rejection_reason": quality.rejection_reason,
                    "sharpness": quality.sharpness,
                    "min_dimension": quality.min_dimension,
                },
            )

        # 6. Align and extract normalized embedding
        aligned_face = self.cv_engine.aligner.align(image, face_detection)
        embedding_vector = self.cv_engine.embedder.extract_embedding(aligned_face)
        preview_ok, preview_encoded = cv2.imencode(
            ".jpg", aligned_face, [cv2.IMWRITE_JPEG_QUALITY, 82]
        )
        if not preview_ok:
            raise BiometricProcessingError(
                message="Enrollment failed: could not create the face preview.",
                details={"student_id": student.student_id},
            )

        # 7. Persist FaceTemplate
        template = FaceTemplate(
            student_id=student.id,
            model_name=self.cv_engine.embedder.model_name,
            model_version=self.cv_engine.embedder.model_version,
            embedding_dim=len(embedding_vector),
            quality_score=quality.overall_score,
            sharpness=quality.sharpness,
            is_primary=is_primary,
            enrollment_source="single_reference_photo",
        )
        template.set_embedding_vector(embedding_vector)
        template.preview_blob = preview_encoded.tobytes()
        template.preview_mime_type = "image/jpeg"

        db.add(template)

        # Audit event
        audit = AuditEvent(
            action="FACE_ENROLLED",
            entity_type="face_template",
            entity_id=template.id,
            actor=actor,
            details=json.dumps({
                "student_id": student.student_id,
                "model": f"{template.model_name}:{template.model_version}",
                "quality_score": round(quality.overall_score, 4),
            }),
        )
        db.add(audit)
        db.commit()
        db.refresh(template)

        # 8. Temporary photo non-retention policy
        settings = get_settings()
        if not retain_original_photo and not settings.photo_retention_days > 0:
            if isinstance(image_input, (str, Path)):
                p = Path(image_input)
                # If it is inside temporary uploads directory, delete it
                if p.exists() and "uploads" in str(p):
                    try:
                        p.unlink()
                        logger.debug(f"Purged temporary enrollment image: {p}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temp enrollment image {p}: {e}")

        logger.info(
            f"Successfully enrolled face template for {student.student_id} "
            f"(Model: {template.model_name}:{template.model_version})"
        )
        return template

    @staticmethod
    def get_student_templates(
        db: Session,
        id_or_student_id: str,
        required_model_version: Optional[str] = None,
    ) -> List[FaceTemplate]:
        """
        Retrieves all enrolled templates for a student.
        Optionally filters by model version to avoid comparing incompatible embeddings.
        """
        stmt = select(Student).where(
            (Student.id == id_or_student_id) | (Student.student_id == id_or_student_id)
        )
        student = db.execute(stmt).scalar_one_or_none()
        if not student:
            raise ResourceNotFoundError(resource_type="Student", identifier=id_or_student_id)

        templates = student.templates
        if required_model_version:
            templates = [t for t in templates if t.model_version == required_model_version]

        return templates

    @staticmethod
    def get_aggregated_student_embedding(
        db: Session,
        id_or_student_id: str,
        required_model_version: Optional[str] = None,
    ) -> Optional[np.ndarray]:
        """
        Computes an averaged, unit-normalized reference embedding across
        all registered templates for a student for a specific model version.
        Returns None if no compatible templates exist.
        """
        templates = EnrollmentService.get_student_templates(
            db,
            id_or_student_id,
            required_model_version=required_model_version,
        )
        if not templates:
            return None

        vectors = [t.get_embedding_vector() for t in templates]
        # Average reference vectors
        mean_vector = np.mean(vectors, axis=0)

        # Normalize to unit length: ||v|| = 1.0
        norm = np.linalg.norm(mean_vector)
        if norm > 1e-8:
            mean_vector = mean_vector / norm

        return mean_vector.astype(np.float32)

    @staticmethod
    def delete_template(db: Session, template_id: str, actor: str = "system") -> bool:
        """Deletes an individual face template."""
        stmt = select(FaceTemplate).where(FaceTemplate.id == template_id)
        template = db.execute(stmt).scalar_one_or_none()
        if not template:
            raise ResourceNotFoundError(resource_type="FaceTemplate", identifier=template_id)

        student_fk = template.student_id
        db.delete(template)

        audit = AuditEvent(
            action="TEMPLATE_DELETED",
            entity_type="face_template",
            entity_id=template_id,
            actor=actor,
            details=json.dumps({"student_id": student_fk}),
        )
        db.add(audit)
        db.commit()

        logger.info(f"Deleted face template: {template_id}")
        return True

    @staticmethod
    def delete_all_student_templates(db: Session, id_or_student_id: str, actor: str = "system") -> int:
        """Deletes all biometric face references for a student."""
        stmt = select(Student).where(
            (Student.id == id_or_student_id) | (Student.student_id == id_or_student_id)
        )
        student = db.execute(stmt).scalar_one_or_none()
        if not student:
            raise ResourceNotFoundError(resource_type="Student", identifier=id_or_student_id)

        count = len(student.templates)
        student.templates.clear()

        audit = AuditEvent(
            action="ALL_TEMPLATES_DELETED",
            entity_type="student",
            entity_id=student.id,
            actor=actor,
            details=json.dumps({"deleted_count": count}),
        )
        db.add(audit)
        db.commit()

        logger.info(f"Deleted all ({count}) face templates for student {student.student_id}")
        return count
