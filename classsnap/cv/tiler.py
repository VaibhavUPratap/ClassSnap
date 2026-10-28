"""
Multi-pass tiled face detection service for high-resolution classroom group photographs.
Enables reliable detection of small, distant student faces in back rows.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

from classsnap.cv.base import FaceDetector
from classsnap.cv.deduplication import non_maximum_suppression, sort_detections_classroom_order
from classsnap.cv.geometry import transform_tile_to_global
from classsnap.cv.types import DetectionResult
from classsnap.logger import get_logger

logger = get_logger("cv.tiler")


@dataclass
class TileGridInfo:
    x: int
    y: int
    w: int
    h: int
    tile_index: int


def generate_overlapping_tiles(
    image_width: int,
    image_height: int,
    tile_size: int = 640,
    overlap_ratio: float = 0.25,
) -> List[TileGridInfo]:
    """
    Generates an overlapping grid of tiles covering the entire image.
    Ensures that borders and corners are covered without dead zones.
    """
    if image_width <= tile_size and image_height <= tile_size:
        return [TileGridInfo(x=0, y=0, w=image_width, h=image_height, tile_index=0)]

    stride_x = max(64, int(tile_size * (1.0 - overlap_ratio)))
    stride_y = max(64, int(tile_size * (1.0 - overlap_ratio)))

    # Compute horizontal start offsets
    x_offsets = list(range(0, image_width - tile_size, stride_x))
    # Ensure the right edge is covered
    if not x_offsets or x_offsets[-1] + tile_size < image_width:
        x_offsets.append(max(0, image_width - tile_size))

    # Compute vertical start offsets
    y_offsets = list(range(0, image_height - tile_size, stride_y))
    # Ensure the bottom edge is covered
    if not y_offsets or y_offsets[-1] + tile_size < image_height:
        y_offsets.append(max(0, image_height - tile_size))

    tiles: List[TileGridInfo] = []
    idx = 0
    for y in y_offsets:
        for x in x_offsets:
            w = min(tile_size, image_width - x)
            h = min(tile_size, image_height - y)
            tiles.append(TileGridInfo(x=x, y=y, w=w, h=h, tile_index=idx))
            idx += 1

    return tiles


class TiledFaceDetector:
    """
    Multi-pass detector that executes full-image detection combined with
    sliding overlapping tile detection to maximize recall on distant, small faces.
    """

    def __init__(
        self,
        base_detector: FaceDetector,
        tile_size: int = 640,
        overlap_ratio: float = 0.25,
        iou_merge_threshold: float = 0.40,
        containment_threshold: float = 0.60,
        run_full_image_pass: bool = True,
    ):
        self.base_detector = base_detector
        self.tile_size = int(tile_size)
        self.overlap_ratio = float(overlap_ratio)
        self.iou_merge_threshold = float(iou_merge_threshold)
        self.containment_threshold = float(containment_threshold)
        self.run_full_image_pass = run_full_image_pass

    def detect(
        self,
        image: np.ndarray,
        score_threshold: Optional[float] = None,
    ) -> List[DetectionResult]:
        """
        Executes multi-pass detection:
        1. (Optional) Full-image detection pass
        2. Tiled detection pass across overlapping crops
        3. Coordinate mapping from tile space to global image space
        4. NMS deduplication
        5. Classroom-order spatial sorting
        """
        img_h, img_w = image.shape[:2]
        all_candidates: List[DetectionResult] = []

        # Pass 1: Full image detection pass
        if self.run_full_image_pass:
            full_detections = self.base_detector.detect(image, score_threshold=score_threshold)
            for d in full_detections:
                d.metadata["detection_pass"] = "full_image"
                all_candidates.append(d)
            logger.debug(f"Full-image pass found {len(full_detections)} candidate(s)")

        # Pass 2: Tiled detection pass
        tiles = generate_overlapping_tiles(
            image_width=img_w,
            image_height=img_h,
            tile_size=self.tile_size,
            overlap_ratio=self.overlap_ratio,
        )

        logger.debug(f"Executing tiled detection over {len(tiles)} tile(s) (size={self.tile_size}, overlap={self.overlap_ratio:.0%})")

        for tile in tiles:
            tile_slice = image[tile.y : tile.y + tile.h, tile.x : tile.x + tile.w]
            if tile_slice.size == 0 or tile_slice.shape[0] < 10 or tile_slice.shape[1] < 10:
                continue

            tile_detections = self.base_detector.detect(tile_slice, score_threshold=score_threshold)

            # Pass 3: Coordinate transformation to global image coordinates
            for td in tile_detections:
                td.metadata["detection_pass"] = "tiled"
                td.metadata["tile_index"] = tile.tile_index
                global_det = transform_tile_to_global(
                    detection=td,
                    tile_offset_x=tile.x,
                    tile_offset_y=tile.y,
                    image_width=img_w,
                    image_height=img_h,
                )
                if global_det is not None:
                    all_candidates.append(global_det)

        logger.debug(f"Total raw candidates before NMS: {len(all_candidates)}")

        # Pass 4: NMS Deduplication
        deduplicated = non_maximum_suppression(
            detections=all_candidates,
            iou_threshold=self.iou_merge_threshold,
            containment_threshold=self.containment_threshold,
        )

        # Pass 5: Spatial classroom-order sorting
        final_detections = sort_detections_classroom_order(deduplicated)

        logger.info(
            f"Multi-pass detection complete: {len(final_detections)} final face(s) from {len(all_candidates)} raw candidate(s)"
        )
        return final_detections
