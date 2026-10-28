"""Consent-governed face enrollment endpoint."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from classsnap.db.session import get_db
from classsnap.schemas.enrollment import EnrollmentResponse
from classsnap.services.enrollment_service import EnrollmentService
from classsnap.api.v1.upload import read_image_upload

router = APIRouter(prefix="/students", tags=["Enrollment"])


@router.post("/{student_id}/enrollment", response_model=EnrollmentResponse)
async def enroll_student_face(
    student_id: str,
    image: UploadFile = File(...),
    consent_granted: bool = Form(False),
    consent_notes: str | None = Form(None),
    is_primary: bool = Form(True),
    actor: str = Form("system"),
    db: Session = Depends(get_db),
):
    template = EnrollmentService().enroll_student_face(
        db,
        student_id,
        await read_image_upload(image),
        consent_granted=consent_granted,
        consent_notes=consent_notes,
        is_primary=is_primary,
        actor=actor,
    )
    student = template.student
    return EnrollmentResponse(
        template_id=template.id,
        student_id=student.student_id,
        student_name=student.full_name,
        model_name=template.model_name,
        model_version=template.model_version,
        embedding_dimension=template.embedding_dim,
        quality_score=template.quality_score,
        sharpness=template.sharpness,
        created_at=template.created_at,
    )
