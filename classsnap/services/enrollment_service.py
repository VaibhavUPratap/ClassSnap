"""
Consent-Based Biometric Face Enrollment Service for ClassSnap.
Handles single-face validation, quality checking, embedding extraction,
multi-reference storage, and aggregated reference vector generation.
"""

import json
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

        # 4. Detect faces (direct single-pass detection on enrollment portrait)
        detections = self.cv_engine.detector.detect(image, score_threshold=0.60)

        if len(detections) == 0:
            raise BiometricProcessingError(
                message="Enrollment failed: No face was detected in the reference photograph. "
                        "Please provide a well-lit, unobstructed front-facing portrait.",
                details={"student_id": student.student_id, "faces_detected": 0},
            )

        if len(detections) > 1:
            raise BiometricProcessingError(
                message=f"Enrollment failed: Multiple faces ({len(detections)}) detected. "
                        f"Enrollment photographs must contain exactly one face.",
                details={"student_id": student.student_id, "faces_detected": len(detections)},
            )

        face_detection = detections[0]

        # 5. Assess face quality
        quality = self.cv_engine.quality_assessor.assess_quality(image, face_detection)
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
