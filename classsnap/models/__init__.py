"""
SQLAlchemy ORM Models Package for ClassSnap.
"""

from classsnap.db.base import Base
from classsnap.models.student import Student
from classsnap.models.face_template import FaceTemplate
from classsnap.models.audit import AuditEvent
from classsnap.models.attendance import (
    AttendanceDetection,
    AttendanceRecord,
    AttendanceSession,
    ProposedMatch,
    ReviewDecision,
)

__all__ = [
    "Base", "Student", "FaceTemplate", "AuditEvent",
    "AttendanceSession", "AttendanceDetection", "ProposedMatch", "ReviewDecision",
    "AttendanceRecord",
]
