"""
OpenCV YuNet face detection implementation for ClassSnap.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union
import cv2
import numpy as np

from classsnap.cv.base import FaceDetector, FaceQualityAssessor
from classsnap.cv.model_registry import validate_model_file
from classsnap.cv.quality import OpenCVFaceQualityAssessor
from classsnap.cv.types import BoundingBox, DetectionResult
from classsnap.exceptions import BiometricProcessingError, ConfigurationError
from classsnap.logger import get_logger

logger = get_logger("cv.detector")


class YuNetFaceDetector(FaceDetector):
    """
    Face detector wrapping OpenCV YuNet (ONNX model).
    Supports dynamic input sizing and structured output with 5 facial landmarks.
    """

    def __init__(
        self,
        model_path: Union[str, Path],
        score_threshold: float = 0.7,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
        quality_assessor: Optional[FaceQualityAssessor] = None,
    ):
        self.model_path = Path(model_path)
        self.metadata = validate_model_file(self.model_path, "yunet")
        self.score_threshold = float(score_threshold)
        self.nms_threshold = float(nms_threshold)
        self.top_k = int(top_k)
        self.quality_assessor = quality_assessor or OpenCVFaceQualityAssessor()

        try:
            self._detector = cv2.FaceDetectorYN.create(
                model=str(self.model_path),
                config="",
                input_size=(320, 320),
                score_threshold=self.score_threshold,
                nms_threshold=self.nms_threshold,
                top_k=self.top_k,
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize OpenCV YuNet detector from {self.model_path}: {e}"
            )

    @property
    def model_name(self) -> str:
        return self.metadata.name

    @property
    def model_version(self) -> str:
        return self.metadata.version

    def detect(
        self,
        image: np.ndarray,
        score_threshold: Optional[float] = None,
    ) -> List[DetectionResult]:
        """
        Executes face detection on an input image.
        Returns a list of structured DetectionResult objects.
        """
        if image is None:
            raise BiometricProcessingError("Input image is None")

        if not isinstance(image, np.ndarray) or image.size == 0:
            raise BiometricProcessingError("Input image is not a valid non-empty NumPy array")

        if len(image.shape) != 3 or image.shape[2] != 3:
            raise BiometricProcessingError(
                f"Input image must be a 3-channel BGR array, got shape: {image.shape}"
            )

        img_h, img_w = image.shape[:2]
        if img_w < 10 or img_h < 10:
            return []

        # YuNet requires setting input size matching the image dimensions
        self._detector.setInputSize((img_w, img_h))

        effective_threshold = score_threshold if score_threshold is not None else self.score_threshold
        self._detector.setScoreThreshold(effective_threshold)

        try:
            _, faces = self._detector.detect(image)
        except Exception as e:
            logger.error(f"YuNet detection failed: {e}")
            raise BiometricProcessingError(f"Detection engine encountered an error: {e}")

        if faces is None or len(faces) == 0:
            return []

        results: List[DetectionResult] = []
        for face in faces:
            # YuNet output layout:
            # [0:4] -> bbox (x, y, w, h)
            # [4:14] -> 5 facial landmarks (right_eye, left_eye, nose_tip, right_mouth, left_mouth)
            # [14] -> confidence score
            bx, by, bw, bh = face[0:4]
            bbox = BoundingBox(x=int(bx), y=int(by), w=int(bw), h=int(bh))
            confidence = float(face[14])

            # Extract 5 landmarks
            landmarks = [
                (float(face[4]), float(face[5])),    # right eye
                (float(face[6]), float(face[7])),    # left eye
                (float(face[8]), float(face[9])),    # nose tip
                (float(face[10]), float(face[11])),  # right mouth corner
                (float(face[12]), float(face[13])),  # left mouth corner
            ]

            det = DetectionResult(
                bbox=bbox,
                confidence=confidence,
                landmarks=landmarks,
                status="detected",
            )

            # Assess quality
            quality = self.quality_assessor.assess_quality(image, det)
            det.quality = quality
            if not quality.is_usable:
                det.status = "low_quality"

            results.append(det)

        return results
