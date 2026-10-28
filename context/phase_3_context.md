# Phase 3 Context — High-Resolution Tiled Face Detection

## Status: COMPLETED

## Deliverables Summary
1. **Coordinate Transformation & Geometry Utilities (`classsnap/cv/geometry.py`)**:
   - `compute_iou`: Intersection-over-Union computation for bounding boxes.
   - `compute_ioa`: Intersection-over-Area for nested/container detection.
   - `clamp_bbox`: Bounds safety, clamping coordinates to valid image dimensions `[0, W]` and `[0, H]`, rejecting out-of-bounds degenerate boxes.
   - `transform_tile_to_global`: Maps tile-local coordinates and 5 facial landmarks to original full-image coordinates with metadata tracking (`tile_origin`).
2. **Detection Deduplication & NMS (`classsnap/cv/deduplication.py`)**:
   - `non_maximum_suppression`: Suppresses redundant boxes across multi-pass and overlapping tiles using IoU (default 0.40) and containment threshold (0.85). Preserves adjacent students sitting close to each other.
   - `sort_detections_classroom_order`: Spatially organizes detections top-to-bottom (back row to front row) and left-to-right across student desks.
3. **Multi-Pass Tiled Detection Pipeline (`classsnap/cv/tiler.py`)**:
   - `generate_overlapping_tiles`: Generates a uniform overlapping grid covering the full image without border/corner dead zones.
   - `TiledFaceDetector`: Executes full-image pass + sliding tile pass + coordinate transformation + NMS deduplication + natural classroom spatial sorting.
4. **Integration into `CVEngine` (`classsnap/cv/engine.py`)**:
   - Automatically utilizes tiled detection for high-resolution images exceeding `tile_size` (default 640px).
5. **Detection Evaluation & Benchmark Framework (`scripts/evaluate_detection.py`)**:
   - Generates high-resolution classroom seating benchmark photos with multiple rows (small distant back-row faces to large front-row faces).
   - Measures True Positives, False Positives, False Negatives, Precision, Recall, F1-Score, and Latency.
   - Compares Full-Image Detection vs. Tiled Detection on the same validation data.
   - Benchmark result on 18-student classroom validation:
     - Full-Image: 16 detected, Recall 88.9%, F1 94.1%, Latency 59.5 ms
     - Tiled Multi-pass: 17 detected, Recall 94.4%, F1 97.1%, Latency 164.4 ms
     - **Recall improvement: +5.5%**, **F1-Score improvement: +3.0%**, Precision maintained at 100.0%.
6. **Automated Test Suite**:
   - 12 new tests in `tests/test_geometry.py` and `tests/test_tiled_detector.py` (total 31 tests passing across the repository).
