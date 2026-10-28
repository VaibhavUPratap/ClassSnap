"""
Student database model for ClassSnap.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from classsnap.db.base import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Student(Base):
    """
    Registered student record.
    """
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    student_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    templates: Mapped[List["FaceTemplate"]] = relationship(
        "FaceTemplate",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __init__(self, **kw):
        if "id" not in kw or kw["id"] is None:
            kw["id"] = _new_uuid()
        super().__init__(**kw)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"<Student(student_id='{self.student_id}', name='{self.full_name}', active={self.is_active})>"
