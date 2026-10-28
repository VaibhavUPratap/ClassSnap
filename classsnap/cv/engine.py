"""
Unified Computer Vision Engine Facade for ClassSnap.
Orchestrates face detection, quality assessment, landmark alignment,
feature embedding extraction, and annotated visualization.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union
import cv2
import numpy as np

from classsnap.config import Settings, get_settings
from classsnap.cv.aligner import SimilarityTransformAligner
from classsnap.cv.annotator import OpenCVFaceAnnotator
from classsnap.cv.base import (
    EmbeddingExtractor,
    FaceAligner,
    FaceAnnotator,
    FaceDetector,
    FaceQualityAssessor,
)
from classsnap.cv.detector import YuNetFaceDetector
from classsnap.cv.embedder import SFaceEmbeddingExtractor
from classsnap.cv.quality import OpenCVFaceQualityAssessor
from classsnap.cv.tiler import TiledFaceDetector
from classsnap.cv.types import DetectionResult
from classsnap.exceptions import BiometricProcessingError, ValidationError
from classsnap.logger import get_logger

logger = get_logger("cv.engine")


class CVEngine:
    """
    High-level Computer Vision Engine orchestrating detection and recognition.
    """

    def __init__(
        self,
        detector: FaceDetector,
        aligner: FaceAligner,
        embedder: EmbeddingExtractor,
        quality_assessor: FaceQualityAssessor,
        annotator: FaceAnnotator,
        tiled_detector: Optional[TiledFaceDetector] = None,
    ):
        self.detector = detector
        self.aligner = aligner
        self.embedder = embedder
        self.quality_assessor = quality_assessor
        self.annotator = annotator
        self.tiled_detector = tiled_detector or TiledFaceDetector(base_detector=detector)

    @classmethod
    def from_settings(cls, settings: Optional[Settings] = None) -> "CVEngine":
        """Builds CVEngine from configured model paths."""
        cfg = settings or get_settings()
        detector = YuNetFaceDetector(
            model_path=cfg.yunet_model_path,
            score_threshold=cfg.detection_score_threshold,
        )
        aligner = SimilarityTransformAligner()
        embedder = SFaceEmbeddingExtractor(model_path=cfg.sface_model_path)
        quality_assessor = OpenCVFaceQualityAssessor()
        annotator = OpenCVFaceAnnotator()

        tiled_detector = TiledFaceDetector(
            base_detector=detector,
            tile_size=cfg.tile_size,
            overlap_ratio=cfg.tile_overlap,
            iou_merge_threshold=cfg.iou_merge_threshold,
            run_full_image_pass=True,
        )

        return cls(
            detector=detector,
            aligner=aligner,
            embedder=embedder,
            quality_assessor=quality_assessor,
            annotator=annotator,
            tiled_detector=tiled_detector,
        )

    @staticmethod
    def load_image(source: Union[str, Path, bytes, np.ndarray]) -> np.ndarray:
        """
        Loads and validates an image from a filepath, raw bytes, or existing numpy array.
        Returns a valid BGR uint8 NumPy array.
        """
        if source is None:
            raise ValidationError("Image source is None")

        if isinstance(source, np.ndarray):
            if source.size == 0 or len(source.shape) != 3 or source.shape[2] != 3:
                raise ValidationError("Supplied numpy image is not a valid 3-channel array")
            return source

        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                raise ValidationError(f"Image file does not exist: {path}")
            if not path.is_file():
                raise ValidationError(f"Path is not a regular file: {path}")

            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                raise ValidationError(f"Failed to decode image file (corrupted or unsupported format): {path}")
            return image

        if isinstance(source, bytes):
            if len(source) == 0:
                raise ValidationError("Image byte buffer is empty")
            arr = np.frombuffer(source, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValidationError("Failed to decode image from provided byte buffer")
            return image

        raise ValidationError(f"Unsupported image input type: {type(source)}")

    def process_image(
        self,
        image_input: Union[str, Path, bytes, np.ndarray],
        score_threshold: Optional[float] = None,
        extract_embeddings: bool = True,
        use_tiling: bool = True,
    ) -> Tuple[List[DetectionResult], np.ndarray]:
        """
        Processes a classroom or enrollment image:
        1. Loads and validates image format
        2. Detects all visible faces (via full-image or multi-pass tiled detection)
        3. Assesses quality for each detection
        4. Aligns and extracts normalized 128D embeddings for usable faces
        5. Generates annotated image visualization
        Returns (detections, annotated_bgr_image)
        """
        image = self.load_image(image_input)
        img_h, img_w = image.shape[:2]

        # 1. Detect faces (choose tiled if enabled and image exceeds tile size, else single pass)
        if use_tiling and (img_w > self.tiled_detector.tile_size or img_h > self.tiled_detector.tile_size):
            detections = self.tiled_detector.detect(image, score_threshold=score_threshold)
            logger.info(f"Tiled detection found {len(detections)} face candidate(s)")
        else:
            detections = self.detector.detect(image, score_threshold=score_threshold)
            logger.info(f"Direct detection found {len(detections)} face candidate(s)")

        # 2. Process each detection for alignment and embedding
        for det in detections:
            if extract_embeddings and det.quality.is_usable:
                try:
                    aligned_face = self.aligner.align(image, det)
                    embedding_vec = self.embedder.extract_embedding(aligned_face)
                    det.embedding = embedding_vec.tolist()
                except Exception as e:
                    logger.warning(f"Failed to extract embedding for detection {det.detection_id}: {e}")
                    det.quality.is_usable = False
                    det.quality.rejection_reason = f"Embedding extraction failed: {str(e)}"
                    det.status = "embedding_error"

        # 3. Generate annotated image
        annotated = self.annotator.annotate(image, detections)

        return detections, annotated
