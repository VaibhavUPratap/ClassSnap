"""
FaceTemplate database model for ClassSnap.
"""

import uuid
import numpy as np
from sqlalchemy import Boolean, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from classsnap.db.base import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class FaceTemplate(Base):
    __tablename__ = "face_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )

    model_name: Mapped[str] = mapped_column(String(50), nullable=False, default="SFace")
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="2021dec")
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False, default=128)
    embedding_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    preview_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    preview_mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    sharpness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enrollment_source: Mapped[str] = mapped_column(String(100), default="single_photo", nullable=False)

    student: Mapped["Student"] = relationship("Student", back_populates="templates")

    def __init__(self, **kw):
        if "id" not in kw or kw["id"] is None:
            kw["id"] = _new_uuid()
        super().__init__(**kw)

    def get_embedding_vector(self) -> np.ndarray:
        vec = np.frombuffer(self.embedding_blob, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-8:
            vec = vec / norm
        return vec

    def set_embedding_vector(self, vector: np.ndarray) -> None:
        vec = vector.flatten().astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-8:
            vec = vec / norm
        self.embedding_blob = vec.tobytes()
        self.embedding_dim = len(vec)

    def __repr__(self) -> str:
        return f"<FaceTemplate(id='{self.id}', student_id='{self.student_id}', model='{self.model_name}:{self.model_version}')>"
