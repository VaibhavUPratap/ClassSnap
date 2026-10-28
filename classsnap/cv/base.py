"""
Abstract base classes and interfaces for the ClassSnap Computer Vision Engine.
Enables pluggable detectors (YuNet, SCRFD, RetinaFace) and embedders (SFace, ArcFace).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np

from classsnap.cv.types import DetectionResult, FaceQuality


class FaceDetector(ABC):
    """Abstract interface for face detection models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the detector model."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Version identifier of the detector model."""
        pass

    @abstractmethod
    def detect(
        self,
        image: np.ndarray,
        score_threshold: Optional[float] = None,
    ) -> List[DetectionResult]:
        """
        Detects faces in a BGR image.
        Returns a list of structured DetectionResult objects.
        """
        pass


class FaceAligner(ABC):
    """Abstract interface for face alignment."""

    @abstractmethod
    def align(
        self,
        image: np.ndarray,
        detection: DetectionResult,
        target_size: Tuple[int, int] = (112, 112),
    ) -> np.ndarray:
        """
        Aligns and crops a face from the source image based on detection landmarks/bbox.
        Returns normalized/cropped face image ready for embedding extraction.
        """
        pass


class EmbeddingExtractor(ABC):
    """Abstract interface for face recognition / feature embedding models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the recognition model."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Version identifier of the recognition model."""
        pass

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Dimensionality of the output embedding vector."""
        pass

    @abstractmethod
    def extract_embedding(self, face_image: np.ndarray) -> np.ndarray:
        """
        Extracts a normalized numerical embedding vector from a cropped/aligned face image.
        """
        pass


class FaceQualityAssessor(ABC):
    """Abstract interface for assessing face quality and suitability for recognition."""

    @abstractmethod
    def assess_quality(
        self,
        image: np.ndarray,
        detection: DetectionResult,
    ) -> FaceQuality:
        """
        Estimates quality parameters (sharpness, brightness, contrast, size)
        and determines if the face is usable for identity recognition.
        """
        pass


class FaceAnnotator(ABC):
    """Abstract interface for generating visual annotated images."""

    @abstractmethod
    def annotate(
        self,
        image: np.ndarray,
        detections: List[DetectionResult],
        highlight_id: Optional[str] = None,
    ) -> np.ndarray:
        """
        Draws bounding boxes, landmarks, confidence, and status labels onto an image copy.
        """
        pass
