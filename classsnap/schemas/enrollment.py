"""
Pydantic schemas for Biometric Face Enrollment.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class EnrollmentConsentPayload(BaseModel):
    consent_granted: bool = Field(..., description="Explicit affirmation of student consent")
    consent_notes: Optional[str] = Field(None, description="Reference to consent agreement form")


class EnrollmentResponse(BaseModel):
    template_id: str
    student_id: str
    student_name: str
    model_name: str
    model_version: str
    embedding_dimension: int
    quality_score: float
    sharpness: float
    created_at: datetime
    message: str = "Student successfully enrolled."
