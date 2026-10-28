"""
AuditEvent database model for ClassSnap.
"""

import uuid
from typing import Optional
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from classsnap.db.base import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __init__(self, **kw):
        if "id" not in kw or kw["id"] is None:
            kw["id"] = _new_uuid()
        super().__init__(**kw)

    def __repr__(self) -> str:
        return f"<AuditEvent(action='{self.action}', entity='{self.entity_type}:{self.entity_id}')>"
