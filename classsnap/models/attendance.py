"""Attendance session persistence models."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
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
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    detections: Mapped[List["AttendanceDetection"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="AttendanceDetection.sequence"
    )
    attendance: Mapped[List["AttendanceRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    review_decisions: Mapped[List["ReviewDecision"]] = relationship(
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


class AttendanceRecord(Base):
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

    session: Mapped["AttendanceSession"] = relationship(back_populates="attendance")
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_session_student_attendance"),)
