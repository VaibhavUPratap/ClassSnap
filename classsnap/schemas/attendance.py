"""API schemas for attendance session workflows."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AttendanceSessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    class_at: datetime | None = Field(None, description="Date and time when the class took place")
    actor: str = Field("system", min_length=1, max_length=100)


class AttendanceSessionResponse(BaseModel):
    id: str
    name: str
    status: str
    created_by: str
    class_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    confirmed_by: Optional[str] = None


class AttendanceDetectionResponse(BaseModel):
    detection_id: str
    status: str
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    student_usn: Optional[str] = None
    similarity: Optional[float] = None
    rejection_reason: Optional[str] = None
    reviewed: bool
    preview_url: Optional[str] = None
    bbox: Optional[dict] = None
    candidate_student_id: Optional[str] = None
    candidate_student_name: Optional[str] = None


class RosterAttendanceEntry(BaseModel):
    """One roster student's proposed (or, once confirmed, final) attendance."""

    student_id: str = Field(..., description="Internal student primary key")
    student_usn: str
    student_name: str
    status: str = Field(
        ...,
        description="Proposed: present | absent | needs_review | not_detected. "
        "Confirmed: present | absent | unverified.",
    )
    auto_status: Optional[str] = None
    recognition_status: str = Field(
        ..., description="matched | ambiguous | not_detected | manual"
    )
    detection_id: Optional[str] = None
    similarity: Optional[float] = None
    preview_url: Optional[str] = None
    manually_set: bool = False
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None
    notes: Optional[str] = None
    attendance_id: Optional[str] = None
    verification_method: Optional[str] = None
    reviewed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    corrected_by: Optional[str] = None
    correction_reason: Optional[str] = None


class AttendanceSessionDetailResponse(AttendanceSessionResponse):
    detections: list[AttendanceDetectionResponse] = Field(default_factory=list)
    attendance: list[RosterAttendanceEntry] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
    confirmation_problems: list[str] = Field(default_factory=list)


class StudentAttendanceUpdate(BaseModel):
    status: Literal["present", "absent"]
    actor: str = Field("system", min_length=1, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)


class AttendanceConfirmRequest(BaseModel):
    actor: str = Field(..., min_length=1, max_length=100)


class SessionHistoryItem(BaseModel):
    session_id: str
    session_name: str
    status: str
    class_date: datetime
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    total_registered: int = 0
    present_count: int = 0
    absent_count: int = 0
    unverified_count: int = 0


class StudentSessionAttendance(BaseModel):
    session_id: str
    session_name: str
    class_date: datetime
    status: str
    verification_method: Optional[str] = None
    confirmed_at: Optional[datetime] = None


class StudentAttendanceHistory(BaseModel):
    student_id: str
    student_usn: str
    student_name: str
    total_sessions: int
    sessions_attended: int
    sessions_absent: int
    sessions_unverified: int
    attendance_rate: Optional[float] = None
    sessions: list[StudentSessionAttendance] = Field(default_factory=list)


class AttendanceProposal(BaseModel):
    detection_id: str = Field(..., min_length=1, max_length=100)
    status: str = Field(..., min_length=1, max_length=32)
    student_id: Optional[str] = None
    similarity: Optional[float] = None
    rejection_reason: Optional[str] = None


class AttendanceProposalRequest(BaseModel):
    proposals: list[AttendanceProposal] = Field(default_factory=list)
    actor: str = Field("system", min_length=1, max_length=100)


class AttendanceReviewRequest(BaseModel):
    student_id: Optional[str] = None
    present: bool
    actor: str = Field("system", min_length=1, max_length=100)
    notes: Optional[str] = None


class AttendanceCorrectionRequest(AttendanceReviewRequest):
    reason: str = Field(..., min_length=1, max_length=1000)


class AttendanceReviewResponse(BaseModel):
    id: str
    status: str
    student_id: Optional[str]
    reviewed: bool
