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

        # 4. Detect faces, including a contrast-enhanced fallback for dark portraits.
        detections = self.cv_engine.detector.detect(image, score_threshold=0.40)
        if not any(min(d.bbox.w, d.bbox.h) >= 80 for d in detections):
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            lightness, chroma_a, chroma_b = cv2.split(lab)
            enhanced = cv2.createCLAHE(
                clipLimit=2.0, tileGridSize=(8, 8)
            ).apply(lightness)
            enhanced_image = cv2.cvtColor(
                cv2.merge((enhanced, chroma_a, chroma_b)), cv2.COLOR_LAB2BGR
            )
            detections = self.cv_engine.detector.detect(
                enhanced_image, score_threshold=0.40
            )
        if len(detections) == 0:
            raise BiometricProcessingError(
                message="Enrollment failed: No face was detected in the reference photograph. "
                        "Please provide a well-lit, unobstructed front-facing portrait.",
                details={"student_id": student.student_id, "faces_detected": 0},
            )

        large_detections = [
            detection for detection in detections if min(detection.bbox.w, detection.bbox.h) >= 80
        ]
        candidate_detections = large_detections or detections
        if len(candidate_detections) > 1:
            # YuNet can return overlapping partial boxes for one large, dark face.
            # Collapse those boxes before applying the single-face enrollment rule.
            remaining = list(candidate_detections)
            grouped = []
            while remaining:
                candidate = remaining.pop(0)
                group = [candidate]
                for other in remaining[:]:
                    left = max(candidate.bbox.x, other.bbox.x)
                    top = max(candidate.bbox.y, other.bbox.y)
                    right = min(
                        candidate.bbox.x + candidate.bbox.w,
                        other.bbox.x + other.bbox.w,
                    )
                    bottom = min(
                        candidate.bbox.y + candidate.bbox.h,
                        other.bbox.y + other.bbox.h,
                    )
                    intersection = max(0, right - left) * max(0, bottom - top)
                    smaller_area = min(
                        candidate.bbox.w * candidate.bbox.h,
                        other.bbox.w * other.bbox.h,
                    )
                    if smaller_area and intersection / smaller_area >= 0.40:
                        group.append(other)
                        remaining.remove(other)
                grouped.append(max(group, key=lambda item: item.bbox.w * item.bbox.h))
            candidate_detections = grouped
        if not candidate_detections:
            raise BiometricProcessingError(
                message=(
                    "Enrollment failed: no sufficiently large face was detected. "
                    "Use a clear portrait where the face is prominent."
                ),
                details={"student_id": student.student_id, "faces_detected": len(detections)},
            )
        if len(candidate_detections) > 1:
            raise BiometricProcessingError(
                message=f"Enrollment failed: Multiple faces ({len(candidate_detections)}) detected. "
                        "Enrollment photographs must contain exactly one face.",
                details={
                    "student_id": student.student_id,
                    "faces_detected": len(candidate_detections),
                },
            )
        face_detection = candidate_detections[0]

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
