"""
Pydantic schemas for Student Roster and Management.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


USN_PATTERN = r"^[A-Z]{3}\d{2}[A-Z]{2}\d{4}$"


class StudentBase(BaseModel):
    student_id: str = Field(
        ...,
        pattern=USN_PATTERN,
        description="Unique USN in the format ENG24AM0107",
        json_schema_extra={"example": "ENG24AM0107"},
    )
    first_name: str = Field(..., min_length=1, max_length=100, description="First name", json_schema_extra={"example": "Alice"})
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name", json_schema_extra={"example": "Johnson"})
    email: Optional[str] = Field(None, max_length=255, description="Institutional email", json_schema_extra={"example": "alice.j@university.edu"})
    has_consent: bool = Field(False, description="Whether explicit biometric consent has been recorded")
    consent_notes: Optional[str] = Field(None, max_length=255, description="Consent documentation or form reference")


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    has_consent: Optional[bool] = None
    consent_notes: Optional[str] = None


class FaceTemplateSummary(BaseModel):
    id: str
    model_name: str
    model_version: str
    embedding_dim: int
    quality_score: float
    sharpness: float
    is_primary: bool
    created_at: datetime


class StudentResponse(StudentBase):
    id: str
    is_active: bool
    consent_recorded_at: Optional[datetime]
    created_at: datetime
    enrolled_templates_count: int = 0
    templates: List[FaceTemplateSummary] = []


class RosterImportError(BaseModel):
    row_number: int
    student_id: Optional[str]
    error_message: str


class RosterImportSummary(BaseModel):
    total_processed: int
    imported_count: int
    skipped_count: int
    errors: List[RosterImportError] = []
