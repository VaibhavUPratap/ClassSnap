"""
Deduplication and Non-Maximum Suppression (NMS) utilities for multi-pass face detection.
"""

from typing import List, Optional
from classsnap.cv.geometry import compute_ioa, compute_iou
from classsnap.cv.types import DetectionResult
from classsnap.logger import get_logger

logger = get_logger("cv.deduplication")


def non_maximum_suppression(
    detections: List[DetectionResult],
    iou_threshold: float = 0.40,
    containment_threshold: float = 0.60,
) -> List[DetectionResult]:
    """
    Suppresses duplicate face detections across full-image and tile passes.

    Uses IoU and containment ratio (IoA) to eliminate multiple detections of the same face
    while preserving adjacent students seated closely next to each other.

    Args:
        detections: List of DetectionResult candidates.
        iou_threshold: Maximum allowable IoU between distinct face detections (default 0.40).
        containment_threshold: Ratio at which a smaller nested box is treated as a duplicate.
            A lower threshold handles oversized classroom portraits where the detector can
            emit a second box around only part of the same face.

    Returns:
        Deduplicated list of DetectionResult objects sorted by confidence.
    """
    if not detections:
        return []

    # Sort descending by confidence score
    candidates = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept: List[DetectionResult] = []

    for cand in candidates:
        is_duplicate = False
        for k in kept:
            iou = compute_iou(cand.bbox, k.bbox)
            if iou >= iou_threshold:
                is_duplicate = True
                break

            ioa_cand, ioa_k = compute_ioa(cand.bbox, k.bbox)
            # If one box is almost entirely contained within another higher-confidence box
            if ioa_cand >= containment_threshold or ioa_k >= containment_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append(cand)

    logger.debug(f"NMS suppressed {len(detections) - len(kept)} duplicate detection(s), kept {len(kept)}")
    return kept


def sort_detections_classroom_order(
    detections: List[DetectionResult],
    row_height_tolerance: int = 50,
) -> List[DetectionResult]:
    """
    Sorts face detections in natural classroom order:
    Top row to bottom row (back-of-classroom to front-of-classroom),
    and left-to-right within each row.
    """
    if not detections:
        return []

    # Sort by Y coordinate first
    sorted_by_y = sorted(detections, key=lambda d: d.bbox.y)

    rows: List[List[DetectionResult]] = []
    current_row: List[DetectionResult] = []
    current_row_y: Optional[int] = None

    for det in sorted_by_y:
        if current_row_y is None:
            current_row = [det]
            current_row_y = det.bbox.y
        elif abs(det.bbox.y - current_row_y) <= row_height_tolerance:
            current_row.append(det)
        else:
            # Sort previous row left-to-right
            rows.append(sorted(current_row, key=lambda d: d.bbox.x))
            current_row = [det]
            current_row_y = det.bbox.y

    if current_row:
        rows.append(sorted(current_row, key=lambda d: d.bbox.x))

    # Flatten rows
    flattened: List[DetectionResult] = []
    for r in rows:
        flattened.extend(r)

    return flattened
