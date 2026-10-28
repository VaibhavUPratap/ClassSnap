"""
Unit and integration tests for tiled face detection, deduplication, and metrics.
"""

from pathlib import Path
import numpy as np
import pytest

from classsnap.cv.deduplication import non_maximum_suppression, sort_detections_classroom_order
from classsnap.cv.detector import YuNetFaceDetector
from classsnap.cv.tiler import TiledFaceDetector, generate_overlapping_tiles
from classsnap.cv.types import BoundingBox, DetectionResult
from scripts.evaluate_detection import calculate_detection_metrics


def test_generate_overlapping_tiles_coverage():
    img_w, img_h = 1200, 800
    tile_size = 500
    overlap = 0.2

    tiles = generate_overlapping_tiles(
        image_width=img_w,
        image_height=img_h,
        tile_size=tile_size,
        overlap_ratio=overlap,
    )

    assert len(tiles) > 1
    # Check that the bottom-right corner is covered
    has_right_edge = any(t.x + t.w >= img_w for t in tiles)
    has_bottom_edge = any(t.y + t.h >= img_h for t in tiles)
    assert has_right_edge is True
    assert has_bottom_edge is True


def test_non_maximum_suppression_removes_duplicates():
    # Two detections of the same face with 0.8 IoU
    d1 = DetectionResult(
        bbox=BoundingBox(x=100, y=100, w=50, h=50),
        confidence=0.92,
    )
    d2 = DetectionResult(
        bbox=BoundingBox(x=105, y=102, w=50, h=50),
        confidence=0.75,
    )

    # Distinct adjacent student face (only 0.05 overlap or adjacent)
    d3 = DetectionResult(
        bbox=BoundingBox(x=160, y=100, w=50, h=50),
        confidence=0.88,
    )

    result = non_maximum_suppression([d1, d2, d3], iou_threshold=0.40)
    assert len(result) == 2
    # Ensure d1 (higher confidence) was kept over d2
    confidences = [d.confidence for d in result]
    assert 0.92 in confidences
    assert 0.88 in confidences
    assert 0.75 not in confidences


def test_non_maximum_suppression_removes_nested_false_face_box():
    outer = DetectionResult(
        bbox=BoundingBox(x=495, y=480, w=366, h=440),
        confidence=0.92,
    )
    nested = DetectionResult(
        bbox=BoundingBox(x=596, y=405, w=272, h=219),
        confidence=0.87,
    )

    result = non_maximum_suppression([outer, nested])

    assert result == [outer]


def test_sort_detections_classroom_order():
    # Row 1 (back row, y ~ 100)
    d_r1_c2 = DetectionResult(bbox=BoundingBox(x=300, y=105, w=40, h=40), confidence=0.9)
    d_r1_c1 = DetectionResult(bbox=BoundingBox(x=100, y=98, w=40, h=40), confidence=0.9)

    # Row 2 (front row, y ~ 300)
    d_r2_c2 = DetectionResult(bbox=BoundingBox(x=250, y=302, w=60, h=60), confidence=0.9)
    d_r2_c1 = DetectionResult(bbox=BoundingBox(x=80, y=295, w=60, h=60), confidence=0.9)

    unordered = [d_r2_c2, d_r1_c2, d_r2_c1, d_r1_c1]
    ordered = sort_detections_classroom_order(unordered, row_height_tolerance=40)

    # Expected order: d_r1_c1 -> d_r1_c2 -> d_r2_c1 -> d_r2_c2
    assert ordered[0].bbox.x == 100 and ordered[0].bbox.y == 98
    assert ordered[1].bbox.x == 300 and ordered[1].bbox.y == 105
    assert ordered[2].bbox.x == 80 and ordered[2].bbox.y == 295
    assert ordered[3].bbox.x == 250 and ordered[3].bbox.y == 302


def test_calculate_detection_metrics_perfect():
    gt = [
        BoundingBox(x=10, y=10, w=50, h=50),
        BoundingBox(x=100, y=10, w=50, h=50),
    ]
    preds = [
        BoundingBox(x=12, y=11, w=50, h=50),  # Matches GT 1
        BoundingBox(x=99, y=12, w=50, h=50),  # Matches GT 2
    ]

    metrics = calculate_detection_metrics(predictions=preds, ground_truth=gt, iou_threshold=0.5)
    assert metrics["true_positives"] == 2
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0


def test_calculate_detection_metrics_partial():
    gt = [
        BoundingBox(x=10, y=10, w=50, h=50),
        BoundingBox(x=100, y=10, w=50, h=50),  # Missed
    ]
    preds = [
        BoundingBox(x=10, y=10, w=50, h=50),  # TP
        BoundingBox(x=500, y=500, w=50, h=50),  # FP
    ]

    metrics = calculate_detection_metrics(predictions=preds, ground_truth=gt, iou_threshold=0.5)
    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1_score"] == 0.5


def test_tiled_face_detector_integration_no_out_of_bounds():
    yunet_path = Path("models/face_detection_yunet_2023mar.onnx")
    if not yunet_path.exists():
        pytest.skip("YuNet model file not present")

    base_detector = YuNetFaceDetector(model_path=yunet_path, score_threshold=0.5)
    tiler = TiledFaceDetector(
        base_detector=base_detector,
        tile_size=400,
        overlap_ratio=0.25,
        iou_merge_threshold=0.40,
    )

    # Empty large canvas
    img = np.zeros((900, 1200, 3), dtype=np.uint8)
    dets = tiler.detect(img)
    assert len(dets) == 0

    # Ensure coordinates are within canvas bounds
    sample_path = Path("tests/assets/sample_face.jpg")
    if sample_path.exists():
        import cv2
        sample = cv2.imread(str(sample_path))
        # Place face in canvas near boundary
        img[50:50 + sample.shape[0], 50:50 + sample.shape[1]] = sample
        results = tiler.detect(img)
        for r in results:
            assert r.bbox.x >= 0
            assert r.bbox.y >= 0
            assert r.bbox.x2 <= 1200
            assert r.bbox.y2 <= 900
            assert r.bbox.w > 0
            assert r.bbox.h > 0
