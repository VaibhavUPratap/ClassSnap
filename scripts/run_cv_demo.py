#!/usr/bin/env python3
"""
CLI demonstration script for ClassSnap Computer Vision Engine.
Usage:
    python scripts/run_cv_demo.py [path_to_image] [--output annotated.jpg]
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import cv2
from classsnap.cv.engine import CVEngine


def main():
    parser = argparse.ArgumentParser(description="ClassSnap CV Engine Demonstration")
    parser.add_argument(
        "image",
        help="Path to a classroom or face photograph",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="uploads/annotated_demo.jpg",
        help="Path to save annotated image (default: uploads/annotated_demo.jpg)",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.7,
        help="Confidence score threshold (default: 0.7)",
    )

    args = parser.parse_args()
    image_path = Path(args.image)

    if not image_path.exists():
        print(f"[ERROR] Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print(f"ClassSnap Computer Vision Engine — Running on: {image_path}")
    print("=" * 60)

    engine = CVEngine.from_settings()
    detections, annotated = engine.process_image(str(image_path), score_threshold=args.threshold)

    print(f"\n[+] Total Faces Detected: {len(detections)}")
    for i, det in enumerate(detections, start=1):
        status_flag = "USABLE" if det.quality.is_usable else f"UNUSABLE ({det.quality.rejection_reason})"
        print(f"\nFace #{i}:")
        print(f"  - Detection ID: {det.detection_id}")
        print(f"  - Bounding Box: (x={det.bbox.x}, y={det.bbox.y}, w={det.bbox.w}, h={det.bbox.h})")
        print(f"  - Confidence:   {det.confidence * 100:.1f}%")
        print(f"  - Quality:      {status_flag}")
        print(f"  - Sharpness:    {det.quality.sharpness:.1f}")
        print(f"  - Has Embedding: {det.embedding is not None} (dimension: {len(det.embedding) if det.embedding else 0})")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), annotated)
    print(f"\n[OK] Saved annotated image to: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
