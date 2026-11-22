"""Small-face recovery: upscaled detection/alignment and the match review band."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from classsnap.cv.aligner import SimilarityTransformAligner
from classsnap.cv.engine import CVEngine
from classsnap.cv.quality import OpenCVFaceQualityAssessor
from classsnap.cv.types import BoundingBox, DetectionResult, FaceQuality
from classsnap.services.matching_service import (
    STATUS_AMBIGUOUS,
    STATUS_MATCHED,
    MatchingService,
    MatchingThresholds,
)


def _engine(detector=None, **kwargs):
    embedder = MagicMock()
    embedder.extract_embedding.side_effect = lambda face: np.ones(128, np.float32) / np.sqrt(128)
    return CVEngine(
        detector=detector or MagicMock(),
        aligner=SimilarityTransformAligner(),
        embedder=embedder,
        quality_assessor=OpenCVFaceQualityAssessor(min_face_size=12, min_sharpness=0.0, min_contrast=0.0),
        annotator=MagicMock(annotate=lambda image, dets: image),
        **kwargs,
    )


@pytest.mark.parametrize(
    "shape, factor",
    [((960, 1280), 3.0), ((1440, 1920), 2.0), ((1920, 2560), 1.5), ((3000, 4000), 1.0), ((200, 200), 3.0)],
)
def test_detection_upscale_targets_small_photos_only(shape, factor):
    engine = _engine()
    assert engine.detection_upscale(np.zeros(shape + (3,), np.uint8)) == pytest.approx(factor)


def _textured(h, w):
    rng = np.random.default_rng(0)
    return rng.integers(40, 220, size=(h, w, 3), dtype=np.uint8)


def test_process_image_detects_on_upscaled_photo_and_maps_back():
    seen = {}

    def detect(image, score_threshold=None):
        seen["shape"] = image.shape
        # 18 px face at (300, 150) in original coordinates, reported at 3x.
        x, y, s = 300 * 3, 150 * 3, 18 * 3
        lm = [(x + s * 0.3, y + s * 0.4), (x + s * 0.7, y + s * 0.4), (x + s * 0.5, y + s * 0.6),
              (x + s * 0.35, y + s * 0.8), (x + s * 0.65, y + s * 0.8)]
        tiny = (10 * 3, 10 * 3)  # 10 px in the original: below the 12 px floor
        return [
            DetectionResult(bbox=BoundingBox(x, y, s, s), confidence=0.9, landmarks=lm, quality=FaceQuality()),
            DetectionResult(bbox=BoundingBox(30, 30, *tiny), confidence=0.9, landmarks=None, quality=FaceQuality()),
        ]

    engine = _engine(detector=MagicMock(detect=detect))
    image = _textured(480, 640)
    detections, _ = engine.process_image(image, use_tiling=False)

    assert seen["shape"][:2] == (480 * 3, 640 * 3)
    assert len(detections) == 1
    face = detections[0]
    assert (face.bbox.x, face.bbox.y, face.bbox.w) == (300, 150, 18)
    assert face.landmarks[0] == pytest.approx((300 + 18 * 0.3, 150 + 18 * 0.4))
    assert face.quality.is_usable and face.embedding is not None


def test_large_photo_keeps_native_resolution():
    detector = MagicMock()
    detector.detect.return_value = []
    engine = _engine(detector=detector)
    engine.process_image(_textured(3000, 4000), use_tiling=False)
    assert detector.detect.call_args.args[0].shape[:2] == (3000, 4000)


def test_align_for_recognition_matches_full_upscale_alignment():
    import cv2

    image = _textured(300, 400)
    det = DetectionResult(
        bbox=BoundingBox(200, 100, 20, 20),
        confidence=0.9,
        landmarks=[(206.0, 108.0), (214.0, 108.0), (210.0, 112.0), (207.0, 116.0), (213.0, 116.0)],
    )
    engine = _engine()
    local = engine.align_for_recognition(image, det)

    up = cv2.resize(image, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    full = SimilarityTransformAligner().align(
        up, DetectionResult(bbox=BoundingBox(600, 300, 60, 60), confidence=0.9,
                            landmarks=[(x * 3, y * 3) for x, y in det.landmarks])
    )
    assert local.shape == (112, 112, 3)
    assert np.abs(local.astype(int) - full.astype(int)).mean() < 6


def _vec(*values):
    v = np.zeros(8, np.float32)
    v[: len(values)] = values
    return v / np.linalg.norm(v)


def test_scores_between_accept_and_auto_accept_need_review():
    service = MatchingService()  # accept 0.38, auto_accept 0.42
    roster = {"a": ("A", _vec(1, 0, 0)), "b": ("B", _vec(0, 1, 0))}

    borderline = service.match_single("f1", _vec(0.40, 0, np.sqrt(1 - 0.40 ** 2)), roster)
    assert borderline.status == STATUS_AMBIGUOUS
    assert borderline.top_candidate.student_id == "a"
    assert "review band" in borderline.rejection_reason

    confident = service.match_single("f2", _vec(0.50, 0, np.sqrt(1 - 0.50 ** 2)), roster)
    assert confident.status == STATUS_MATCHED


def test_custom_accept_above_auto_accept_is_unchanged():
    thresholds = MatchingThresholds(accept=0.8, ambiguity_gap=0.05)
    assert thresholds.effective_auto_accept == 0.8
    result = MatchingService(thresholds).match_single(
        "f", _vec(1, 0), {"a": ("A", _vec(1, 0)), "b": ("B", _vec(0, 1))}
    )
    assert result.status == STATUS_MATCHED
