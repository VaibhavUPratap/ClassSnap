# Phase 25: Robust Enrollment for Dark and Partial Face Detections

## Status

Completed on 2026-10-29.

## Delivered

- Enrollment detection now uses a lower confidence threshold (`0.40`) so
  real faces are not hidden by small background graphics.
- Dark-image fallback applies CLAHE contrast enhancement when no sufficiently
  large face is found in the original image.
- Tiny face-like graphics are ignored when a larger face candidate exists.
- Overlapping partial detections from one face are grouped before enforcing
  the single-face enrollment rule.
- Separate faces still fail enrollment with the existing multiple-face error.
- Added regression coverage for overlapping partial detections.
- Re-enrolled Abhishek's active template from the supplied image during live
  verification. The supplied `uploads/abhishek.jpeg` file is no longer
  present in the working tree, so a fresh exact-image verification requires
  that file to be restored.

## Validation

- Full backend suite: 80 passed, 2 skipped.
- Enrollment suite: 13 tests collected, 12 passed, 1 skipped.
- `git diff --check`: passed.
- Available supplied images continue to process without runtime errors.
