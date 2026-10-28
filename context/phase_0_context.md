# Phase 0 Context — Requirements Analysis and System Architecture

## Summary
Phase 0 established the foundational system architecture and design principles for ClassSnap.

## Core Directives
1. **Model Modularization**:
   - `cv.detector.FaceDetector` interface with YuNet implementation, ready for SCRFD/RetinaFace.
   - `cv.embedder.FaceEmbedder` interface with SFace implementation, ready for ArcFace.
   - Normalized 128D/512D embeddings compared with cosine similarity.
2. **Matching & Uncertainty**:
   - Status classifications: `matched_pending_review`, `unknown`, `low_quality`, `ambiguous`, `no_candidate`.
   - Bipartite matching (Hungarian algorithm) for 1-to-1 face assignment.
   - Rejection threshold preventing forced assignments.
3. **Privacy & Security**:
   - Consent recording prior to enrollment.
   - Student reference embeddings stored with model version tracking.
   - Classroom group photos deleted by default after session attendance finalization.
   - No biometric data in Git.
4. **Human Review Workflow**:
   - Draft -> Processing -> Review Required -> Confirmed.
   - Absences require explicit human review; never marked absent purely due to non-detection.
