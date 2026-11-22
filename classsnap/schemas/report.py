"""Attendance report response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class AttendanceReportStudent(BaseModel):
    student_id: str
    student_name: str


class AttendanceReportSession(BaseModel):
    session_id: str
    session_name: str
    class_date: datetime
    class_section: str | None = None
    confirmed_at: datetime | None = None
    confirmed_by: str | None = None
    present_count: int
    absent_count: int
    unverified_count: int = 0
    total_registered: int = 0
    attendees: list[AttendanceReportStudent] = Field(default_factory=list)


class AttendanceReportSummary(BaseModel):
    total_sessions: int
    total_attendance: int
    total_possible: int
    sessions: list[AttendanceReportSession] = Field(default_factory=list)
