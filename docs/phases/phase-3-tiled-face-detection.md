# Phase 3 — High-Resolution Tiled Face Detection

## Goal
Improve small-face detection in classroom photos via configurable tiled inference.

## Required outputs
- Multi-pass detection: full image + overlapping tiles
- Coordinate transform utilities (tile → full image)
- Duplicate removal (NMS/merge)
- Final sorted detections and visualization
- Configurable tile size, overlap, confidence, detector input size
- IoU-based evaluation script and metrics (precision/recall/F1)
- Full-image vs tiled comparison on labeled data

## Acceptance criteria
Coordinates remain accurate, duplicates are controlled, and measurable full-vs-tiled results are produced.
