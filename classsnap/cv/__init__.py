"""
ClassSnap Computer Vision Engine Package.
"""

from classsnap.cv.base import (
    EmbeddingExtractor,
    FaceAligner,
    FaceAnnotator,
    FaceDetector,
    FaceQualityAssessor,
)
from classsnap.cv.types import BoundingBox, DetectionResult, FaceQuality
from classsnap.cv.aligner import SimilarityTransformAligner
from classsnap.cv.annotator import OpenCVFaceAnnotator
from classsnap.cv.deduplication import non_maximum_suppression, sort_detections_classroom_order
from classsnap.cv.detector import YuNetFaceDetector
from classsnap.cv.embedder import SFaceEmbeddingExtractor
from classsnap.cv.engine import CVEngine
from classsnap.cv.geometry import (
    clamp_bbox,
    compute_ioa,
    compute_iou,
    transform_tile_to_global,
)
from classsnap.cv.model_registry import validate_model_file
from classsnap.cv.quality import OpenCVFaceQualityAssessor
from classsnap.cv.tiler import TiledFaceDetector, generate_overlapping_tiles

__all__ = [
    "BoundingBox",
    "DetectionResult",
    "FaceQuality",
    "FaceDetector",
    "FaceAligner",
    "EmbeddingExtractor",
    "FaceQualityAssessor",
    "FaceAnnotator",
    "YuNetFaceDetector",
    "SFaceEmbeddingExtractor",
    "OpenCVFaceQualityAssessor",
    "SimilarityTransformAligner",
    "OpenCVFaceAnnotator",
    "CVEngine",
    "validate_model_file",
    "compute_iou",
    "compute_ioa",
    "clamp_bbox",
    "transform_tile_to_global",
    "non_maximum_suppression",
    "sort_detections_classroom_order",
    "TiledFaceDetector",
    "generate_overlapping_tiles",
]
