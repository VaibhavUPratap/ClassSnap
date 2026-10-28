"""Student roster API endpoints."""

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from classsnap.db.session import get_db
from classsnap.schemas.student import (
    RosterImportSummary,
    StudentCreate,
    StudentResponse,
    StudentUpdate,
)
from classsnap.services.roster_service import RosterService

router = APIRouter(prefix="/students", tags=["Roster"])


def _student_response(student) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        student_id=student.student_id,
        first_name=student.first_name,
        last_name=student.last_name,
        email=student.email,
        has_consent=student.has_consent,
        consent_notes=student.consent_notes,
        is_active=student.is_active,
        consent_recorded_at=student.consent_recorded_at,
        created_at=student.created_at,
        enrolled_templates_count=len(student.templates),
        templates=student.templates,
    )


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    actor: str = Query("system", min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    return _student_response(RosterService.create_student(db, payload, actor))


@router.get("", response_model=list[StudentResponse])
def list_students(
    active_only: bool = False,
    limit: int = Query(500, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return [_student_response(student) for student in RosterService.get_students(db, active_only, limit, offset)]


@router.post("/import", response_model=RosterImportSummary)
async def import_roster(
    file: UploadFile = File(...),
    actor: str = Query("system", min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    return RosterService.import_roster_from_csv(await file.read(), actor)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: str, db: Session = Depends(get_db)):
    return _student_response(RosterService.get_student_by_id(db, student_id))


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: str,
    payload: StudentUpdate,
    actor: str = Query("system", min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    return _student_response(RosterService.update_student(db, student_id, payload, actor))


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: str,
    actor: str = Query("system", min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    RosterService.delete_student(db, student_id, actor)
