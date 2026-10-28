# Phase 5 Context — Identity Matching and Uncertainty Handling

## Status: COMPLETED

## Deliverables
1. **Matching service** (`classsnap/services/matching_service.py`):
   - Deterministic cosine-similarity ranking with normalized candidate vectors.
   - Explicit statuses: `matched_pending_review`, `unknown`, `low_quality`,
     `ambiguous`, and `no_candidate`.
   - Acceptance and top-two separation thresholds.
   - Model-version filtering and embedding-dimension validation.
   - Deterministic one-to-one assignment so a student cannot be assigned to
     multiple detections.
   - Structured candidate scores and rejection reasons in `MatchResult`.
2. **Calibration utility**:
   - `CalibrationSample` and `calibrate_thresholds` derive an acceptance
     threshold from labeled genuine/impostor embedding pairs.
   - Calibration rejects incomplete or non-separable datasets.
3. **Test coverage** (`tests/test_matching_service.py`):
   - Known, unknown, ambiguous, low-quality, duplicate, empty-roster,
     model-version mismatch, calibration, and threshold paths.
4. **Validation**:
   - 57 tests passing across the repository.

## Continuation
Phase 6 is next: attendance session lifecycle, proposed matches, review
decisions, transactional confirmation, and audit-safe persistence.
