"""Attendance session persistence models."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from classsnap.db.base import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    class_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)
    # When set, only active students of this class form the session roster.
    class_section: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    detections: Mapped[List["AttendanceDetection"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="AttendanceDetection.sequence"
    )
    attendance: Mapped[List["AttendanceRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    review_decisions: Mapped[List["ReviewDecision"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    proposed_attendance: Mapped[List["ProposedAttendance"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class AttendanceDetection(Base):
    __tablename__ = "attendance_detections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    detection_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    bbox_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preview_blob: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    preview_mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    session: Mapped["AttendanceSession"] = relationship(back_populates="detections")
    proposed_match: Mapped[Optional["ProposedMatch"]] = relationship(
        back_populates="detection", cascade="all, delete-orphan", uselist=False
    )
    __table_args__ = (UniqueConstraint("session_id", "detection_id", name="uq_session_detection"),)


class ProposedMatch(Base):
    __tablename__ = "proposed_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    detection_row_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attendance_detections.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    student_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    similarity: Mapped[Optional[float]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Best roster candidate for ambiguous faces. It is never treated as an
    # identity assignment; it only flags that student for manual verification.
    candidate_student_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )

    detection: Mapped["AttendanceDetection"] = relationship(back_populates="proposed_match")


class ReviewDecision(Base):
    """Immutable audit record for each human review action."""

    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    detection_row_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attendance_detections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    original_student_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    selected_student_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["AttendanceSession"] = relationship(back_populates="review_decisions")


# Proposed (pre-confirmation) roster statuses.
PROPOSED_PRESENT = "present"
PROPOSED_ABSENT = "absent"
PROPOSED_NEEDS_REVIEW = "needs_review"
PROPOSED_NOT_DETECTED = "not_detected"
PROPOSED_STATUSES = {PROPOSED_PRESENT, PROPOSED_ABSENT, PROPOSED_NEEDS_REVIEW, PROPOSED_NOT_DETECTED}

# Final (confirmed) attendance statuses.
FINAL_PRESENT = "present"
FINAL_ABSENT = "absent"
FINAL_UNVERIFIED = "unverified"


class ProposedAttendance(Base):
    """Editable, per-student attendance proposal for a session under review.

    Kept separate from ``AttendanceRecord`` so that nothing is final until an
    authorized reviewer confirms the session.
    """

    __tablename__ = "proposed_attendance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    # What the recognition pipeline proposed before any human edits.
    auto_status: Mapped[str] = mapped_column(String(32), nullable=False)
    detection_row_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("attendance_detections.id", ondelete="SET NULL"), nullable=True
    )
    similarity: Mapped[Optional[float]] = mapped_column(nullable=True)
    manually_set: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["AttendanceSession"] = relationship(back_populates="proposed_attendance")
    detection: Mapped[Optional["AttendanceDetection"]] = relationship()
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_session_student_proposal"),)


class AttendanceRecord(Base):
    """Final, confirmed attendance. ``id`` is the attendance_id."""

    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="review")
    attendance_status: Mapped[str] = mapped_column(String(32), nullable=False, default=FINAL_PRESENT)
    detection_row_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("attendance_detections.id", ondelete="SET NULL"), nullable=True
    )
    verification_method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    corrected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    corrected_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    correction_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["AttendanceSession"] = relationship(back_populates="attendance")
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_session_student_attendance"),)
