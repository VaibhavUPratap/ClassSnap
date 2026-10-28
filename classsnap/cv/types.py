"""
Data types and structured detection models for the ClassSnap Computer Vision Engine.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import uuid


@dataclass
class BoundingBox:
    """Bounding box in pixel coordinates (x, y, width, height)."""
    x: int
    y: int
    w: int
    h: int

    def __post_init__(self):
        self.x = max(0, int(round(self.x)))
        self.y = max(0, int(round(self.y)))
        self.w = max(0, int(round(self.w)))
        self.h = max(0, int(round(self.h)))

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def area(self) -> int:
        return self.w * self.h

    @property
    def aspect_ratio(self) -> float:
        return float(self.w) / float(self.h) if self.h > 0 else 0.0

    def to_xywh(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    def to_xyxy(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x2, self.y2)

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


@dataclass
class FaceQuality:
    """Estimated quality metrics for a detected face."""
    overall_score: float = 1.0
    sharpness: float = 0.0
    brightness: float = 0.0
    contrast: float = 0.0
    min_dimension: int = 0
    is_usable: bool = True
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 4),
            "sharpness": round(self.sharpness, 2),
            "brightness": round(self.brightness, 2),
            "contrast": round(self.contrast, 2),
            "min_dimension": self.min_dimension,
            "is_usable": self.is_usable,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class DetectionResult:
    """Structured result for an individual face detected in an image."""
    bbox: BoundingBox
    confidence: float
    detection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    landmarks: Optional[List[Tuple[float, float]]] = None
    quality: FaceQuality = field(default_factory=FaceQuality)
    status: str = "detected"
    embedding: Optional[List[float]] = None
    crop_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": self.detection_id,
            "bbox": self.bbox.to_dict(),
            "confidence": round(self.confidence, 4),
            "landmarks": self.landmarks,
            "quality": self.quality.to_dict(),
            "status": self.status,
            "has_embedding": self.embedding is not None,
            "embedding_dim": len(self.embedding) if self.embedding else 0,
            "metadata": self.metadata,
        }
