"""
Face annotation utility for ClassSnap.
Renders bounding boxes, confidence tags, facial landmarks, and quality badges on images.
"""

from typing import List, Optional, Tuple
import cv2
import numpy as np

from classsnap.cv.base import FaceAnnotator
from classsnap.cv.types import DetectionResult


# Color palette in BGR format
COLOR_USABLE = (46, 204, 113)       # Emerald Green
COLOR_UNUSABLE = (41, 128, 185)     # Warm Amber/Orange
COLOR_HIGHLIGHT = (241, 196, 15)    # Bright Cyan/Yellow
COLOR_LANDMARK = (231, 76, 60)      # Vivid Blue / Red in BGR
COLOR_BADGE_BG = (25, 25, 25)       # Dark Slate for text background
COLOR_TEXT = (255, 255, 255)        # Pure White


class OpenCVFaceAnnotator(FaceAnnotator):
    """
    Renders clean, professional visual indicators on classroom photographs.
    """

    def __init__(self, draw_landmarks: bool = True, show_confidence: bool = True):
        self.draw_landmarks = draw_landmarks
        self.show_confidence = show_confidence

    def annotate(
        self,
        image: np.ndarray,
        detections: List[DetectionResult],
        highlight_id: Optional[str] = None,
    ) -> np.ndarray:
        output = image.copy()
        img_h, img_w = output.shape[:2]

        for idx, det in enumerate(detections):
            bbox = det.bbox
            is_highlighted = (highlight_id is not None and det.detection_id == highlight_id)

            # Determine primary color based on quality and highlight state
            if is_highlighted:
                box_color = COLOR_HIGHLIGHT
                thickness = 3
            elif not det.quality.is_usable:
                box_color = COLOR_UNUSABLE
                thickness = 2
            else:
                box_color = COLOR_USABLE
                thickness = 2

            # 1. Draw bounding box
            cv2.rectangle(
                output,
                (bbox.x, bbox.y),
                (bbox.x2, bbox.y2),
                box_color,
                thickness=thickness,
            )

            # 2. Draw landmarks if available
            if self.draw_landmarks and det.landmarks:
                for pt in det.landmarks:
                    px, py = int(round(pt[0])), int(round(pt[1]))
                    if 0 <= px < img_w and 0 <= py < img_h:
                        cv2.circle(output, (px, py), 2, COLOR_LANDMARK, -1)

            # 3. Draw informative label badge
            short_id = det.detection_id[:4]
            conf_str = f"{det.confidence * 100:.0f}%" if self.show_confidence else ""
            status_tag = "LOW_Q" if not det.quality.is_usable else f"#{idx + 1}"
            label = f"{status_tag} {conf_str}".strip()

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            font_thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)

            badge_y1 = max(0, bbox.y - text_h - 8)
            badge_y2 = bbox.y
            badge_x1 = bbox.x
            badge_x2 = min(img_w, bbox.x + text_w + 8)

            # Draw badge background
            cv2.rectangle(output, (badge_x1, badge_y1), (badge_x2, badge_y2), COLOR_BADGE_BG, -1)
            cv2.rectangle(output, (badge_x1, badge_y1), (badge_x2, badge_y2), box_color, 1)

            # Put text
            cv2.putText(
                output,
                label,
                (badge_x1 + 4, badge_y2 - 4),
                font,
                font_scale,
                COLOR_TEXT,
                font_thickness,
                lineType=cv2.LINE_AA,
            )

        return output
