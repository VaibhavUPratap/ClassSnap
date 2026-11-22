"""
Unified Computer Vision Engine Facade for ClassSnap.
Orchestrates face detection, quality assessment, landmark alignment,
feature embedding extraction, and annotated visualization.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union
from io import BytesIO
import cv2
import numpy as np
from PIL import Image, ImageOps

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
from classsnap.cv.deduplication import non_maximum_suppression
from classsnap.cv.embedder import SFaceEmbeddingExtractor
from classsnap.cv.quality import OpenCVFaceQualityAssessor
from classsnap.cv.tiler import TiledFaceDetector
from classsnap.cv.types import BoundingBox, DetectionResult
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
        small_face_target_side: int = 3840,
        max_detection_upscale: float = 3.0,
    ):
        self.detector = detector
        self.aligner = aligner
        self.embedder = embedder
        self.quality_assessor = quality_assessor
        self.annotator = annotator
        self.tiled_detector = tiled_detector or TiledFaceDetector(base_detector=detector)
        self.small_face_target_side = small_face_target_side
        self.max_detection_upscale = max_detection_upscale

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
        quality_assessor = OpenCVFaceQualityAssessor(min_face_size=cfg.min_face_size_px)
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
            small_face_target_side=cfg.small_face_target_side,
            max_detection_upscale=cfg.max_detection_upscale,
        )

    # ------------------------------------------------------------ small faces

    def detection_upscale(self, image: np.ndarray) -> float:
        """Upscale factor used for detection/alignment (1.0 = native resolution).

        Messaging apps shrink classroom photos to ~1280 px, leaving back-row
        faces 12-24 px wide: below what YuNet localises reliably and far below
        SFace's 112 px input. Measured on enrollment photos degraded to those
        sizes, detecting and aligning on a 3x bicubic upscale raised genuine
        SFace similarity by ~0.04 and 16 px rank-1 accuracy from 13/16 to 15/16.
        """
        longest = max(image.shape[:2])
        factor = min(self.max_detection_upscale, self.small_face_target_side / max(longest, 1))
        return float(factor) if factor >= 1.5 else 1.0

    @staticmethod
    def _rescale_detection(detection: DetectionResult, factor: float) -> DetectionResult:
        box = detection.bbox
        detection.bbox = BoundingBox(
            x=int(round(box.x * factor)),
            y=int(round(box.y * factor)),
            w=max(1, int(round(box.w * factor))),
            h=max(1, int(round(box.h * factor))),
        )
        if detection.landmarks:
            detection.landmarks = [(x * factor, y * factor) for x, y in detection.landmarks]
        return detection

    def align_for_recognition(self, image: np.ndarray, detection: DetectionResult) -> np.ndarray:
        """Align a face for SFace, resampling small faces bicubically first.

        Equivalent to aligning from the whole upscaled photo, but only the
        region around this face is upscaled.
        """
        factor = self.detection_upscale(image)
        if factor == 1.0 or not detection.landmarks:
            return self.aligner.align(image, detection)
        img_h, img_w = image.shape[:2]
        box = detection.bbox
        margin = max(box.w, box.h)
        x1, y1 = max(0, int(box.x - margin)), max(0, int(box.y - margin))
        x2, y2 = min(img_w, int(box.x2 + margin)), min(img_h, int(box.y2 + margin))
        region = cv2.resize(
            image[y1:y2, x1:x2], None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC
        )
        local = DetectionResult(
            bbox=BoundingBox(
                x=int(round((box.x - x1) * factor)),
                y=int(round((box.y - y1) * factor)),
                w=max(1, int(round(box.w * factor))),
                h=max(1, int(round(box.h * factor))),
            ),
            confidence=detection.confidence,
            landmarks=[((x - x1) * factor, (y - y1) * factor) for x, y in detection.landmarks],
        )
        return self.aligner.align(region, local)

    @staticmethod
    def _composite_bgra_to_bgr(image: np.ndarray) -> np.ndarray:
        """Composites an image over an opaque white background, ensuring uint8 BGR output."""
        if image.dtype == np.uint16:
            image = (image / 257.0).astype(np.uint8)
        elif image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.ndim == 3 and image.shape[2] == 4:
            b, g, r, a = cv2.split(image)
            alpha = a.astype(np.float32) / 255.0
            bgr = cv2.merge((b, g, r)).astype(np.float32)
            white = np.full_like(bgr, 255.0)
            composited = (bgr * alpha[..., None] + white * (1.0 - alpha[..., None])).astype(np.uint8)
            return composited
        if image.ndim == 3 and image.shape[2] == 1:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image

    @staticmethod
    def _pil_decode_oriented(source: Union[str, Path, bytes]) -> Optional[np.ndarray]:
        """Decode using Pillow so EXIF orientation is applied before CV processing."""
        try:
            stream = source if isinstance(source, (str, Path)) else BytesIO(source)
            with Image.open(stream) as pil_image:
                oriented = ImageOps.exif_transpose(pil_image)
                if oriented.mode in ("RGBA", "LA"):
                    rgba = oriented.convert("RGBA")
                    array = np.asarray(rgba)
                    return cv2.cvtColor(array, cv2.COLOR_RGBA2BGRA)
                rgb = oriented.convert("RGB")
                array = np.asarray(rgb)
                return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        except Exception:
            return None

    @classmethod
    def load_image(cls, source: Union[str, Path, bytes, np.ndarray]) -> np.ndarray:
        """
        Loads and validates an image from a filepath, raw bytes, or existing numpy array.
        Returns a valid BGR uint8 NumPy array with transparency composited onto white.
        """
        if source is None:
            raise ValidationError("Image source is None")

        if isinstance(source, np.ndarray):
            if source.size == 0 or source.ndim != 3:
                raise ValidationError("Supplied numpy image is not a valid 3-channel array")
            image = source
            if image.shape[2] == 4:
                image = cls._composite_bgra_to_bgr(image)
            elif image.shape[2] != 3:
                raise ValidationError("Supplied numpy image must be grayscale or 3/4-channel")
            if image.dtype != np.uint8:
                image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            return np.ascontiguousarray(image)

        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                raise ValidationError(f"Image file does not exist: {path}")
            if not path.is_file():
                raise ValidationError(f"Path is not a regular file: {path}")

            image = cls._pil_decode_oriented(path)
            if image is None:
                image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                if image is None:
                    raise ValidationError(f"Failed to decode image file (corrupted or unsupported format): {path}")
            image = cls._composite_bgra_to_bgr(image)
            if image.dtype != np.uint8:
                image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            return np.ascontiguousarray(image)

        if isinstance(source, bytes):
            if len(source) == 0:
                raise ValidationError("Image byte buffer is empty")
            image = cls._pil_decode_oriented(source)
            if image is None:
                arr = np.frombuffer(source, dtype=np.uint8)
                image = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
                if image is None:
                    raise ValidationError("Failed to decode image from provided byte buffer")
            image = cls._composite_bgra_to_bgr(image)
            if image.dtype != np.uint8:
                image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            return np.ascontiguousarray(image)

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
        factor = self.detection_upscale(image)
        work = image if factor == 1.0 else cv2.resize(
            image, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC
        )
        work_h, work_w = work.shape[:2]

        # 1. Detect faces (tiled when the working image exceeds one tile)
        if use_tiling and (work_w > self.tiled_detector.tile_size or work_h > self.tiled_detector.tile_size):
            detections = self.tiled_detector.detect(work, score_threshold=score_threshold)
            logger.info(f"Tiled detection found {len(detections)} face candidate(s) at {factor:.2f}x")
        else:
            detections = self.detector.detect(work, score_threshold=score_threshold)
            logger.info(f"Direct detection found {len(detections)} face candidate(s) at {factor:.2f}x")

        if factor != 1.0:
            detections = [self._rescale_detection(d, 1.0 / factor) for d in detections]
            # Judge quality on the photo's real pixels, not the interpolated ones.
            for detection in detections:
                detection.quality = self.quality_assessor.assess_quality(image, detection)
                detection.status = "detected" if detection.quality.is_usable else "low_quality"

        # Never send degenerately small detections into alignment, embedding,
        # identity matching, or the human-review queue. This is separate from
        # the match threshold and prevents tiny false boxes from becoming proposals.
        detections = [
            detection
            for detection in detections
            if min(detection.bbox.w, detection.bbox.h)
            >= getattr(self.quality_assessor, "min_face_size", 24)
        ]
        detections = non_maximum_suppression(detections)

        # 2. Process each detection for alignment and embedding
        for det in detections:
            if extract_embeddings and det.quality.is_usable:
                try:
                    aligned_face = self.align_for_recognition(image, det)
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
