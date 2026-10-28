# Phase 20: Attendance Matching Verification and Duplicate Suppression

## Status

Completed on 2026-10-28.

## Findings and fix

- The live roster had one enrolled SFace template for `ENG24AM0107`.
- The stored portrait matched that template at cosine similarity `0.9844`.
- The tiled detector also emitted a smaller overlapping false face box, which
  created a second low-similarity `unknown` proposal and made the review appear
  incorrectly absent.
- Lowered the shared containment-based duplicate suppression threshold from
  `0.85` to `0.60` in the tiled detector and NMS utility.
- Added regression coverage for nested false face boxes.

## Validation

- Stored portrait now produces exactly one detection.
- The detection is `matched_pending_review` for the enrolled student with
  similarity `0.9844`.
- `pytest -q tests/test_tiled_detector.py tests/test_attendance_api.py` passed.
- Diagnostic attendance sessions were removed after verification.
