"""API schemas for attendance session workflows."""

from typing import Optional

from pydantic import BaseModel, Field


class AttendanceSessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    actor: str = Field("system", min_length=1, max_length=100)


class AttendanceSessionResponse(BaseModel):
    id: str
    name: str
    status: str
    created_by: str
    confirmed_at: Optional[str] = None


class AttendanceDetectionResponse(BaseModel):
    detection_id: str
    status: str
    student_id: Optional[str] = None
    similarity: Optional[float] = None
    rejection_reason: Optional[str] = None
    reviewed: bool


class AttendanceSessionDetailResponse(AttendanceSessionResponse):
    detections: list[AttendanceDetectionResponse] = Field(default_factory=list)


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
