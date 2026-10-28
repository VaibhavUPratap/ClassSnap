"""
Face alignment and normalization module for ClassSnap.
Performs landmark-based similarity transformation to standardize face orientation.
"""

from typing import List, Optional, Tuple
import cv2
import numpy as np

from classsnap.cv.base import FaceAligner
from classsnap.cv.types import DetectionResult


# Standard 5-point reference landmarks for a 112x112 normalized face crop
# (Right Eye, Left Eye, Nose Tip, Right Mouth Corner, Left Mouth Corner)
REFERENCE_5PTS_112x112 = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


class SimilarityTransformAligner(FaceAligner):
    """
    Standard similarity transform aligner using 5 facial landmarks.
    Falls back to aspect-ratio preserving crop when landmarks are unavailable.
    """

    def __init__(self, output_size: Tuple[int, int] = (112, 112)):
        self.output_size = output_size

    def align(
        self,
        image: np.ndarray,
        detection: DetectionResult,
        target_size: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        size = target_size or self.output_size
        img_h, img_w = image.shape[:2]

        landmarks = detection.landmarks
        if landmarks and len(landmarks) == 5:
            src_pts = np.array(landmarks, dtype=np.float32)

            # Scale reference points if target_size != 112x112
            if size == (112, 112):
                dst_pts = REFERENCE_5PTS_112x112
            else:
                scale_x = size[0] / 112.0
                scale_y = size[1] / 112.0
                dst_pts = REFERENCE_5PTS_112x112 * np.array([scale_x, scale_y], dtype=np.float32)

            # Estimate partial affine similarity matrix (rotation, uniform scale, translation)
            transform_matrix, inliers = cv2.estimateAffinePartial2D(src_pts, dst_pts)
            if transform_matrix is not None:
                aligned = cv2.warpAffine(
                    image,
                    transform_matrix,
                    size,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0, 0, 0),
                )
                return aligned

        # Fallback: direct crop with margin around bounding box
        bbox = detection.bbox
        margin_w = int(bbox.w * 0.15)
        margin_h = int(bbox.h * 0.15)

        x1 = max(0, bbox.x - margin_w)
        y1 = max(0, bbox.y - margin_h)
        x2 = min(img_w, bbox.x2 + margin_w)
        y2 = min(img_h, bbox.y2 + margin_h)

        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return np.zeros((size[1], size[0], 3), dtype=np.uint8)

        return cv2.resize(crop, size, interpolation=cv2.INTER_LINEAR)
