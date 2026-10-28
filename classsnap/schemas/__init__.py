"""
Pydantic Schemas Package for ClassSnap.
"""

from classsnap.schemas.health import HealthCheckResponse
from classsnap.schemas.student import (
    StudentBase,
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    RosterImportSummary,
    RosterImportError,
    FaceTemplateSummary,
)
from classsnap.schemas.enrollment import EnrollmentConsentPayload, EnrollmentResponse

__all__ = [
    "HealthCheckResponse",
    "StudentBase",
    "StudentCreate",
    "StudentUpdate",
    "StudentResponse",
    "RosterImportSummary",
    "RosterImportError",
    "FaceTemplateSummary",
    "EnrollmentConsentPayload",
    "EnrollmentResponse",
]
