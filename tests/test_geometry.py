"""
Unit tests for bounding box geometry, coordinate transformations, and IoU metrics.
"""

import pytest
from classsnap.cv.geometry import (
    clamp_bbox,
    compute_ioa,
    compute_iou,
    transform_tile_to_global,
)
from classsnap.cv.types import BoundingBox, DetectionResult


def test_compute_iou_disjoint():
    b1 = BoundingBox(x=0, y=0, w=50, h=50)
    b2 = BoundingBox(x=100, y=100, w=50, h=50)
    assert compute_iou(b1, b2) == 0.0


def test_compute_iou_identical():
    b1 = BoundingBox(x=20, y=30, w=60, h=80)
    b2 = BoundingBox(x=20, y=30, w=60, h=80)
    assert compute_iou(b1, b2) == 1.0


def test_compute_iou_half_overlap():
    # b1: [0, 0, 100, 100] -> area 10000
    # b2: [50, 0, 100, 100] -> area 10000
    # intersection: [50, 0, 50, 100] -> area 5000
    # union: 10000 + 10000 - 5000 = 15000
    # IoU = 5000 / 15000 = 1/3
    b1 = BoundingBox(x=0, y=0, w=100, h=100)
    b2 = BoundingBox(x=50, y=0, w=100, h=100)
    assert pytest.approx(compute_iou(b1, b2), abs=1e-4) == (1.0 / 3.0)


def test_compute_ioa_nested():
    outer = BoundingBox(x=0, y=0, w=100, h=100)
    inner = BoundingBox(x=20, y=20, w=40, h=40)
    ioa_outer, ioa_inner = compute_ioa(outer, inner)
    assert ioa_inner == 1.0  # inner is 100% inside outer
    assert pytest.approx(ioa_outer, abs=1e-4) == (1600.0 / 10000.0)


def test_clamp_bbox_inside_and_outside():
    # 1. Perfectly inside
    b_inside = BoundingBox(x=10, y=20, w=50, h=50)
    clamped = clamp_bbox(b_inside, max_w=200, max_h=200)
    assert clamped is not None
    assert clamped.x == 10 and clamped.y == 20 and clamped.w == 50 and clamped.h == 50

    # 2. Straddling edge
    b_edge = BoundingBox(x=180, y=190, w=40, h=40)
    clamped_edge = clamp_bbox(b_edge, max_w=200, max_h=200)
    assert clamped_edge is not None
    assert clamped_edge.x2 <= 200
    assert clamped_edge.y2 <= 200
    assert clamped_edge.w == 20
    assert clamped_edge.h == 10

    # 3. Completely outside bounds
    b_out = BoundingBox(x=300, y=300, w=50, h=50)
    clamped_out = clamp_bbox(b_out, max_w=200, max_h=200)
    assert clamped_out is None


def test_transform_tile_to_global():
    det = DetectionResult(
        bbox=BoundingBox(x=15, y=25, w=60, h=70),
        confidence=0.88,
        landmarks=[(30.0, 40.0), (55.0, 40.0), (45.0, 60.0), (35.0, 80.0), (55.0, 80.0)],
    )

    tile_ox, tile_oy = 200, 300
    transformed = transform_tile_to_global(
        detection=det,
        tile_offset_x=tile_ox,
        tile_offset_y=tile_oy,
        image_width=1000,
        image_height=800,
    )

    assert transformed is not None
    assert transformed.bbox.x == 215
    assert transformed.bbox.y == 325
    assert transformed.bbox.w == 60
    assert transformed.bbox.h == 70
    assert transformed.metadata["tile_origin"] == (200, 300)
    assert transformed.landmarks[0] == (230.0, 340.0)
