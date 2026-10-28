"""
Coordinate transformation and bounding box geometry utilities for ClassSnap.
"""

from typing import Optional, Tuple
from classsnap.cv.types import BoundingBox, DetectionResult


def compute_iou(box1: BoundingBox, box2: BoundingBox) -> float:
    """
    Computes Intersection-over-Union (IoU) between two bounding boxes.
    Returns a float in [0.0, 1.0].
    """
    # Intersection coordinates
    inter_x1 = max(box1.x, box2.x)
    inter_y1 = max(box1.y, box2.y)
    inter_x2 = min(box1.x2, box2.x2)
    inter_y2 = min(box1.y2, box2.y2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    if inter_area == 0:
        return 0.0

    union_area = box1.area + box2.area - inter_area
    if union_area <= 0:
        return 0.0

    return float(inter_area / union_area)


def compute_ioa(box1: BoundingBox, box2: BoundingBox) -> Tuple[float, float]:
    """
    Computes Intersection-over-Area for each box:
    (inter_area / box1.area, inter_area / box2.area).
    Useful for identifying when one bounding box is nested inside another.
    """
    inter_x1 = max(box1.x, box2.x)
    inter_y1 = max(box1.y, box2.y)
    inter_x2 = min(box1.x2, box2.x2)
    inter_y2 = min(box1.y2, box2.y2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    ioa1 = inter_area / box1.area if box1.area > 0 else 0.0
    ioa2 = inter_area / box2.area if box2.area > 0 else 0.0
    return (float(ioa1), float(ioa2))


def clamp_bbox(bbox: BoundingBox, max_w: int, max_h: int) -> Optional[BoundingBox]:
    """
    Clamps a bounding box to valid image dimensions [0, max_w] and [0, max_h].
    Returns None if the clamped box has zero area or lies entirely outside the bounds.
    """
    # If the box is entirely outside image dimensions
    if bbox.x >= max_w or bbox.y >= max_h or bbox.x2 <= 0 or bbox.y2 <= 0:
        return None

    x1 = max(0, min(bbox.x, max_w))
    y1 = max(0, min(bbox.y, max_h))
    x2 = max(0, min(bbox.x2, max_w))
    y2 = max(0, min(bbox.y2, max_h))

    w = x2 - x1
    h = y2 - y1

    if w <= 0 or h <= 0:
        return None

    return BoundingBox(x=x1, y=y1, w=w, h=h)


def transform_tile_to_global(
    detection: DetectionResult,
    tile_offset_x: int,
    tile_offset_y: int,
    image_width: int,
    image_height: int,
) -> Optional[DetectionResult]:
    """
    Transforms detection coordinates from tile-relative space to original image space.
    Clamps bounding box and landmarks within the original image boundaries.
    """
    # Transform bounding box
    raw_global_box = BoundingBox(
        x=detection.bbox.x + tile_offset_x,
        y=detection.bbox.y + tile_offset_y,
        w=detection.bbox.w,
        h=detection.bbox.h,
    )

    clamped_box = clamp_bbox(raw_global_box, max_w=image_width, max_h=image_height)
    if clamped_box is None:
        return None

    # Transform 5 landmarks if present
    transformed_landmarks = None
    if detection.landmarks:
        transformed_landmarks = []
        for lx, ly in detection.landmarks:
            gx = min(max(0.0, lx + tile_offset_x), float(image_width - 1))
            gy = min(max(0.0, ly + tile_offset_y), float(image_height - 1))
            transformed_landmarks.append((gx, gy))

    # Create new DetectionResult with global coordinates and metadata
    metadata = dict(detection.metadata)
    metadata["tile_origin"] = (tile_offset_x, tile_offset_y)

    return DetectionResult(
        detection_id=detection.detection_id,
        bbox=clamped_box,
        confidence=detection.confidence,
        landmarks=transformed_landmarks,
        quality=detection.quality,
        status=detection.status,
        embedding=detection.embedding,
        metadata=metadata,
    )
