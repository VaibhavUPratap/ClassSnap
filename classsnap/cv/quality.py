"""
Face Quality Assessment module for ClassSnap.
Evaluates sharpness, illumination, contrast, and size suitability for recognition.
"""

from typing import Optional, Tuple
import cv2
import numpy as np

from classsnap.cv.base import FaceQualityAssessor
from classsnap.cv.types import DetectionResult, FaceQuality


class OpenCVFaceQualityAssessor(FaceQualityAssessor):
    """
    Quality assessor using standard computer vision heuristics:
    - Sharpness / blurriness via Laplacian variance
    - Illumination via mean grayscale intensity
    - Contrast via standard deviation of pixel intensities
    - Resolution via minimum bounding box dimension
    """

    def __init__(
        self,
        min_face_size: int = 24,
        min_sharpness: float = 15.0,
        min_brightness: float = 25.0,
        max_brightness: float = 245.0,
        min_contrast: float = 12.0,
    ):
        self.min_face_size = min_face_size
        self.min_sharpness = min_sharpness
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_contrast = min_contrast

    def assess_quality(
        self,
        image: np.ndarray,
        detection: DetectionResult,
    ) -> FaceQuality:
        bbox = detection.bbox
        img_h, img_w = image.shape[:2]

        # Extract clamped crop
        x1 = max(0, min(bbox.x, img_w - 1))
        y1 = max(0, min(bbox.y, img_h - 1))
        x2 = max(x1 + 1, min(bbox.x2, img_w))
        y2 = max(y1 + 1, min(bbox.y2, img_h))

        crop = image[y1:y2, x1:x2]
        crop_h, crop_w = crop.shape[:2]
        min_dim = min(crop_w, crop_h)

        if crop.size == 0 or min_dim < 4:
            return FaceQuality(
                overall_score=0.0,
                sharpness=0.0,
                brightness=0.0,
                contrast=0.0,
                min_dimension=min_dim,
                is_usable=False,
                rejection_reason="Face crop is empty or degenerately small",
            )

        # Convert to grayscale
        if len(crop.shape) == 3 and crop.shape[2] == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop

        # 1. Sharpness (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian.var())

        # 2. Brightness & Contrast
        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))

        # Check rejection rules
        rejection_reason: Optional[str] = None
        is_usable = True

        if min_dim < self.min_face_size:
            is_usable = False
            rejection_reason = f"Face resolution too small ({min_dim}px < {self.min_face_size}px)"
        elif sharpness < self.min_sharpness:
            is_usable = False
            rejection_reason = f"Face is excessively blurry (sharpness {sharpness:.1f} < {self.min_sharpness})"
        elif brightness < self.min_brightness:
            is_usable = False
            rejection_reason = f"Face severely underexposed (brightness {brightness:.1f} < {self.min_brightness})"
        elif brightness > self.max_brightness:
            is_usable = False
            rejection_reason = f"Face severely overexposed (brightness {brightness:.1f} > {self.max_brightness})"
        elif contrast < self.min_contrast:
            is_usable = False
            rejection_reason = f"Face contrast too low ({contrast:.1f} < {self.min_contrast})"

        # Overall quality score in [0.0, 1.0]
        size_score = min(1.0, min_dim / 80.0)
        sharp_score = min(1.0, sharpness / 100.0)
        bright_score = 1.0 - abs(brightness - 128.0) / 128.0
        contrast_score = min(1.0, contrast / 50.0)

        overall = (
            0.35 * sharp_score +
            0.25 * size_score +
            0.20 * bright_score +
            0.20 * contrast_score
        )
        if not is_usable:
            overall = min(overall, 0.45)

        return FaceQuality(
            overall_score=overall,
            sharpness=sharpness,
            brightness=brightness,
            contrast=contrast,
            min_dimension=min_dim,
            is_usable=is_usable,
            rejection_reason=rejection_reason,
        )
