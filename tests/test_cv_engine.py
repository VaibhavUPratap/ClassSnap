"""
Unit and integration tests for ClassSnap Computer Vision Engine.
Tests model loading, detection, alignment, embedding extraction,
quality assessment, and error handling for invalid/empty inputs.
"""

from pathlib import Path
import numpy as np
import pytest

from classsnap.cv.aligner import SimilarityTransformAligner
from classsnap.cv.annotator import OpenCVFaceAnnotator
from classsnap.cv.detector import YuNetFaceDetector
from classsnap.cv.embedder import SFaceEmbeddingExtractor
from classsnap.cv.engine import CVEngine
from classsnap.cv.model_registry import validate_model_file
from classsnap.cv.quality import OpenCVFaceQualityAssessor
from classsnap.cv.types import BoundingBox, DetectionResult
from classsnap.exceptions import ConfigurationError, ValidationError


ASSETS_DIR = Path(__file__).resolve().parent / "assets"
SAMPLE_FACE = ASSETS_DIR / "sample_face.jpg"
YUNET_PATH = Path("models/face_detection_yunet_2023mar.onnx")
SFACE_PATH = Path("models/face_recognition_sface_2021dec.onnx")


def test_missing_model_raises_configuration_error(tmp_path):
    missing_path = tmp_path / "non_existent_model.onnx"
    with pytest.raises(ConfigurationError) as exc_info:
        validate_model_file(missing_path, "yunet")
    assert "not found" in str(exc_info.value).lower()


def test_invalid_image_inputs():
    with pytest.raises(ValidationError):
        CVEngine.load_image(None)

    with pytest.raises(ValidationError):
        CVEngine.load_image("non_existent_path_file.png")

    with pytest.raises(ValidationError):
        CVEngine.load_image(b"not a valid jpeg or png image data buffer")

    # 2D grayscale array where 3-channel is expected
    with pytest.raises(ValidationError):
        CVEngine.load_image(np.zeros((100, 100), dtype=np.uint8))


def test_empty_image_detection_returns_empty_list():
    detector = YuNetFaceDetector(model_path=YUNET_PATH)
    blank_canvas = np.zeros((400, 400, 3), dtype=np.uint8)

    results = detector.detect(blank_canvas)
    assert isinstance(results, list)
    assert len(results) == 0


def test_quality_assessor_rejects_blurry_and_small_crops():
    assessor = OpenCVFaceQualityAssessor(min_face_size=24, min_sharpness=15.0)

    # 1. Extremely blurry / uniform image
    uniform_img = np.full((100, 100, 3), 128, dtype=np.uint8)
    det_blurry = DetectionResult(
        bbox=BoundingBox(x=10, y=10, w=80, h=80),
        confidence=0.9,
    )
    quality_blurry = assessor.assess_quality(uniform_img, det_blurry)
    assert quality_blurry.sharpness < 5.0
    assert quality_blurry.is_usable is False
    assert "blurry" in quality_blurry.rejection_reason.lower()

    # 2. Too small face crop
    det_tiny = DetectionResult(
        bbox=BoundingBox(x=10, y=10, w=16, h=16),
        confidence=0.85,
    )
    quality_tiny = assessor.assess_quality(uniform_img, det_tiny)
    assert quality_tiny.is_usable is False
    assert "too small" in quality_tiny.rejection_reason.lower()


def test_similarity_transform_aligner():
    aligner = SimilarityTransformAligner(output_size=(112, 112))
    img = np.zeros((200, 200, 3), dtype=np.uint8)

    # With landmarks
    det_with_lm = DetectionResult(
        bbox=BoundingBox(x=40, y=40, w=100, h=100),
        confidence=0.95,
        landmarks=[(60.0, 70.0), (120.0, 70.0), (90.0, 100.0), (70.0, 130.0), (110.0, 130.0)],
    )
    aligned_lm = aligner.align(img, det_with_lm)
    assert aligned_lm.shape == (112, 112, 3)

    # Fallback without landmarks
    det_no_lm = DetectionResult(
        bbox=BoundingBox(x=40, y=40, w=100, h=100),
        confidence=0.95,
        landmarks=None,
    )
    aligned_fallback = aligner.align(img, det_no_lm)
    assert aligned_fallback.shape == (112, 112, 3)


def test_sface_embedding_normalization_and_similarity():
    embedder = SFaceEmbeddingExtractor(model_path=SFACE_PATH)
    assert embedder.embedding_dimension == 128
    assert embedder.model_name == "SFace"

    # Synthetic face crop
    dummy_face = np.full((112, 112, 3), 100, dtype=np.uint8)
    dummy_face[40:50, 40:50] = 200  # pattern

    emb1 = embedder.extract_embedding(dummy_face)
    assert emb1.shape == (128,)
    norm1 = np.linalg.norm(emb1)
    assert pytest.approx(norm1, abs=1e-5) == 1.0

    # Cosine similarity with self is 1.0
    sim_self = SFaceEmbeddingExtractor.compute_cosine_similarity(emb1, emb1)
    assert pytest.approx(sim_self, abs=1e-5) == 1.0


def test_annotator_generation():
    annotator = OpenCVFaceAnnotator()
    base_img = np.zeros((300, 300, 3), dtype=np.uint8)
    det = DetectionResult(
        bbox=BoundingBox(x=50, y=50, w=80, h=80),
        confidence=0.92,
        landmarks=[(70.0, 70.0), (110.0, 70.0), (90.0, 90.0), (75.0, 110.0), (105.0, 110.0)],
    )

    annotated = annotator.annotate(base_img, [det])
    assert annotated.shape == base_img.shape
    # Check that pixels were drawn on annotated copy but base_img remains untouched
    assert np.all(base_img == 0)
    assert np.any(annotated > 0)


@pytest.mark.skipif(not SAMPLE_FACE.exists(), reason="Sample face test photograph not found")
def test_cv_engine_end_to_end_on_valid_photograph():
    engine = CVEngine.from_settings()
    detections, annotated = engine.process_image(str(SAMPLE_FACE))

    assert len(detections) >= 1
    face = detections[0]
    assert face.bbox.w > 50
    assert face.bbox.h > 50
    assert face.confidence > 0.8
    assert face.quality.is_usable is True
    assert face.embedding is not None
    assert len(face.embedding) == 128
    assert annotated.shape[:2] == CVEngine.load_image(str(SAMPLE_FACE)).shape[:2]
