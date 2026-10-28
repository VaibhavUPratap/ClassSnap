"""
Pydantic schemas for Student Roster and Management.
"""

from datetime import datetime
from typing import List, Optional
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


USN_PATTERN = r"[A-Z]{3}[0-9]{2}[A-Z]{2}[0-9]{4}"


class StudentBase(BaseModel):
    student_id: str = Field(
        ...,
        description="Unique USN in the format ENG24AM0107",
        json_schema_extra={"example": "ENG24AM0107"},
    )
    first_name: str = Field(..., min_length=1, max_length=100, description="First name", json_schema_extra={"example": "Alice"})
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name", json_schema_extra={"example": "Johnson"})
    email: Optional[str] = Field(None, max_length=255, description="Institutional email", json_schema_extra={"example": "alice.j@university.edu"})
    has_consent: bool = Field(False, description="Whether explicit biometric consent has been recorded")
    consent_notes: Optional[str] = Field(None, max_length=255, description="Consent documentation or form reference")

    @field_validator("student_id", mode="before")
    @classmethod
    def normalize_usn(cls, value: str) -> str:
        if isinstance(value, str):
            normalized = value.strip().upper()
            if not re.fullmatch(USN_PATTERN, normalized):
                raise ValueError("USN must use the format ENG24AM0107")
            return normalized
        return value


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
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_name: str
    model_version: str
    embedding_dim: int
    quality_score: float
    sharpness: float
    is_primary: bool
    created_at: datetime
    preview_url: Optional[str] = None


class StudentResponse(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    has_consent: bool = False
    consent_notes: Optional[str] = None
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
