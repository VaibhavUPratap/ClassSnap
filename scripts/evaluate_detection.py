#!/usr/bin/env python3
"""
Detection Evaluation & Benchmark Framework for ClassSnap.
Compares Full-Image Face Detection against Overlapping Tiled Detection.
Calculates IoU, Precision, Recall, F1-Score, and Processing Latency.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import cv2
import numpy as np
from classsnap.cv.detector import YuNetFaceDetector
from classsnap.cv.geometry import compute_iou
from classsnap.cv.tiler import TiledFaceDetector
from classsnap.cv.types import BoundingBox, DetectionResult


def calculate_detection_metrics(
    predictions: List[BoundingBox],
    ground_truth: List[BoundingBox],
    iou_threshold: float = 0.50,
) -> Dict[str, Any]:
    """
    Evaluates detector predictions against ground-truth bounding boxes.
    Matches predictions to ground-truth using greedy bipartite IoU matching.
    """
    if not ground_truth:
        return {
            "ground_truth_count": 0,
            "prediction_count": len(predictions),
            "true_positives": 0,
            "false_positives": len(predictions),
            "false_negatives": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "iou_threshold": iou_threshold,
        }

    matched_gt = set()
    matched_pred = set()

    # Precalculate all pair IoUs
    pairs: List[Tuple[float, int, int]] = []
    for p_idx, p_box in enumerate(predictions):
        for gt_idx, gt_box in enumerate(ground_truth):
            iou = compute_iou(p_box, gt_box)
            if iou >= iou_threshold:
                pairs.append((iou, p_idx, gt_idx))

    # Greedy match by highest IoU first
    pairs.sort(key=lambda x: x[0], reverse=True)
    for iou, p_idx, gt_idx in pairs:
        if p_idx not in matched_pred and gt_idx not in matched_gt:
            matched_pred.add(p_idx)
            matched_gt.add(gt_idx)

    tp = len(matched_gt)
    fp = len(predictions) - tp
    fn = len(ground_truth) - tp

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "ground_truth_count": len(ground_truth),
        "prediction_count": len(predictions),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "iou_threshold": iou_threshold,
    }


def create_synthetic_classroom_group_photo(
    sample_face_path: Path,
    output_path: Path,
    canvas_size: Tuple[int, int] = (2600, 1600),
) -> Tuple[np.ndarray, List[BoundingBox]]:
    """
    Synthesizes a realistic high-resolution (2600x1600) classroom seating group photograph:
    - Row 1 (back row, distant small faces ~32px face, 75px head)
    - Row 2 (middle-back row, 110px head)
    - Row 3 (middle-front row, 155px head)
    - Row 4 (front row, foreground students, 215px head)
    Records exact ground-truth face bounding boxes calibrated from the source portrait.
    """
    canvas_w, canvas_h = canvas_size
    canvas = np.full((canvas_h, canvas_w, 3), (210, 215, 220), dtype=np.uint8)

    sample = cv2.imread(str(sample_face_path))
    if sample is None:
        raise ValueError(f"Could not load sample face: {sample_face_path}")

    # Natural head crop including hair/forehead
    sh, sw = sample.shape[:2]
    head_crop = sample[int(sh * 0.1) : int(sh * 0.9), int(sw * 0.2) : int(sw * 0.85)]
    hh, hw = head_crop.shape[:2]

    # Detect exact face box within the reference head crop
    ref_detector = cv2.FaceDetectorYN.create("models/face_detection_yunet_2023mar.onnx", "", (hw, hh))
    _, ref_faces = ref_detector.detect(head_crop)
    if ref_faces is None or len(ref_faces) == 0:
        rf_x, rf_y, rf_w, rf_h = int(hw * 0.2), int(hh * 0.2), int(hw * 0.6), int(hh * 0.6)
    else:
        rf_x, rf_y, rf_w, rf_h = [int(v) for v in ref_faces[0][:4]]

    gt_boxes: List[BoundingBox] = []

    # Classroom 4-row specification
    rows_spec = [
        # Back row: small distant faces
        {"y": 120, "head_height": 75, "count": 6, "spacing": 350},
        # Mid-back row
        {"y": 420, "head_height": 110, "count": 5, "spacing": 420},
        # Mid-front row
        {"y": 800, "head_height": 155, "count": 4, "spacing": 510},
        # Front row: foreground students
        {"y": 1220, "head_height": 215, "count": 3, "spacing": 640},
    ]

    for row in rows_spec:
        target_h = row["head_height"]
        scale = target_h / float(hh)
        target_w = int(round(hw * scale))

        count = row["count"]
        spacing = row["spacing"]
        total_span = (count - 1) * spacing
        start_x = max(60, (canvas_w - total_span - target_w) // 2)

        scaled_head = cv2.resize(head_crop, (target_w, target_h), interpolation=cv2.INTER_AREA)

        # Scaled ground truth face bounding box relative to head
        face_x_rel = int(round(rf_x * scale))
        face_y_rel = int(round(rf_y * scale))
        face_w_rel = int(round(rf_w * scale))
        face_h_rel = int(round(rf_h * scale))

        for col in range(count):
            hx = start_x + col * spacing
            hy = row["y"]

            canvas[hy : hy + target_h, hx : hx + target_w] = scaled_head
            gt_boxes.append(
                BoundingBox(
                    x=hx + face_x_rel,
                    y=hy + face_y_rel,
                    w=face_w_rel,
                    h=face_h_rel,
                )
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), canvas)
    return canvas, gt_boxes


def run_benchmark(
    image: np.ndarray,
    ground_truth: List[BoundingBox],
    tile_size: int = 640,
    overlap_ratio: float = 0.25,
    score_threshold: float = 0.65,
    iou_eval_threshold: float = 0.40,
) -> Dict[str, Any]:
    """
    Executes full-image detection vs. tiled detection on the same image and compares results.
    """
    base_detector = YuNetFaceDetector("models/face_detection_yunet_2023mar.onnx", score_threshold=score_threshold)
    tiled_detector = TiledFaceDetector(
        base_detector=base_detector,
        tile_size=tile_size,
        overlap_ratio=overlap_ratio,
        iou_merge_threshold=0.40,
        run_full_image_pass=True,
    )

    # 1. Full-image detection pass
    t0 = time.perf_counter()
    full_dets = base_detector.detect(image, score_threshold=score_threshold)
    full_time_ms = (time.perf_counter() - t0) * 1000.0
    full_boxes = [d.bbox for d in full_dets]

    full_metrics = calculate_detection_metrics(
        predictions=full_boxes,
        ground_truth=ground_truth,
        iou_threshold=iou_eval_threshold,
    )
    full_metrics["latency_ms"] = round(full_time_ms, 2)

    # 2. Tiled detection pass
    t1 = time.perf_counter()
    tiled_dets = tiled_detector.detect(image, score_threshold=score_threshold)
    tiled_time_ms = (time.perf_counter() - t1) * 1000.0
    tiled_boxes = [d.bbox for d in tiled_dets]

    tiled_metrics = calculate_detection_metrics(
        predictions=tiled_boxes,
        ground_truth=ground_truth,
        iou_threshold=iou_eval_threshold,
    )
    tiled_metrics["latency_ms"] = round(tiled_time_ms, 2)

    return {
        "image_dimensions": {"width": image.shape[1], "height": image.shape[0]},
        "parameters": {
            "tile_size": tile_size,
            "overlap_ratio": overlap_ratio,
            "score_threshold": score_threshold,
            "iou_eval_threshold": iou_eval_threshold,
        },
        "full_image_detection": full_metrics,
        "tiled_detection": tiled_metrics,
        "recall_improvement": round(tiled_metrics["recall"] - full_metrics["recall"], 4),
        "f1_improvement": round(tiled_metrics["f1_score"] - full_metrics["f1_score"], 4),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate Full-Image vs. Tiled Detection")
    parser.add_argument("--tile-size", type=int, default=640, help="Tile dimension (default: 640)")
    parser.add_argument("--overlap", type=float, default=0.25, help="Tile overlap ratio (default: 0.25)")
    parser.add_argument("--threshold", type=float, default=0.65, help="Confidence threshold (default: 0.65)")
    parser.add_argument("--iou", type=float, default=0.40, help="Evaluation IoU threshold (default: 0.40)")
    parser.add_argument("--output-json", default="eval/detection_benchmark.json", help="Path to save benchmark JSON")
    args = parser.parse_args()

    sample_face = Path("tests/assets/sample_face.jpg")
    synth_image_path = Path("eval/classroom_validation.jpg")

    print("=" * 65)
    print("ClassSnap Phase 3 Detection Evaluation & Benchmark")
    print("=" * 65)

    print("[*] Generating high-resolution classroom validation photograph (1600x1000)...")
    image, gt_boxes = create_synthetic_classroom_group_photo(sample_face, synth_image_path)
    print(f"[+] Validation photograph created with {len(gt_boxes)} ground-truth student faces.")

    print("[*] Executing benchmark: Full-Image Detection vs. Tiled Detection...")
    results = run_benchmark(
        image=image,
        ground_truth=gt_boxes,
        tile_size=args.tile_size,
        overlap_ratio=args.overlap,
        score_threshold=args.threshold,
        iou_eval_threshold=args.iou,
    )

    out_file = Path(args.output_json)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print summary table
    fm = results["full_image_detection"]
    tm = results["tiled_detection"]

    print("\n" + "=" * 65)
    print(f"{'Metric':<25} | {'Full-Image':<15} | {'Tiled (Multi-pass)':<15}")
    print("-" * 65)
    print(f"{'Ground Truth Faces':<25} | {fm['ground_truth_count']:<15} | {tm['ground_truth_count']:<15}")
    print(f"{'Detected Faces (TP+FP)':<25} | {fm['prediction_count']:<15} | {tm['prediction_count']:<15}")
    print(f"{'True Positives (TP)':<25} | {fm['true_positives']:<15} | {tm['true_positives']:<15}")
    print(f"{'False Positives (FP)':<25} | {fm['false_positives']:<15} | {tm['false_positives']:<15}")
    print(f"{'False Negatives (FN)':<25} | {fm['false_negatives']:<15} | {tm['false_negatives']:<15}")
    print(f"{'Precision':<25} | {fm['precision'] * 100:.1f}%{'':<10} | {tm['precision'] * 100:.1f}%")
    print(f"{'Recall':<25} | {fm['recall'] * 100:.1f}%{'':<10} | {tm['recall'] * 100:.1f}%")
    print(f"{'F1-Score':<25} | {fm['f1_score'] * 100:.1f}%{'':<10} | {tm['f1_score'] * 100:.1f}%")
    print(f"{'Latency (ms)':<25} | {fm['latency_ms']:.1f} ms{'':<8} | {tm['latency_ms']:.1f} ms")
    print("=" * 65)
    print(f"Recall Delta:   {results['recall_improvement'] * 100:+.1f}%")
    print(f"F1-Score Delta: {results['f1_improvement'] * 100:+.1f}%")
    print(f"[OK] Benchmark JSON written to: {out_file}\n")


if __name__ == "__main__":
    main()
