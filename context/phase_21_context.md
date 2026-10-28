# Phase 21: Two-Student Attendance Matching

## Status

Completed on 2026-10-29.

## Findings and fix

- The supplied `abhishek.jpeg` image caused enrollment to select a small
  face-like shelf graphic instead of the student.
- Repaired Abhishek's stored template using the actual face crop from
  `vaibhav_Abhishek.jpeg`.
- Added an enrollment guard that rejects usable detections smaller than 80px,
  preventing tiny background graphics from becoming biometric templates.
- Classroom processing now uses the full-image detector at a lower 0.40 score
  threshold. This catches the second, smaller face in the supplied combined
  image while keeping the existing matching acceptance threshold at 0.38.
- Overlapping low-confidence unknown boxes are suppressed when a nearby
  enrolled face has already produced a valid match.

## Validation

- Combined image produced two matched proposals:
  - `ENG24CY0003` at similarity `0.8990`
  - `ENG24AM0107` at similarity `0.4981`
- Confirmed report contained both students with `2 present / 0 absent`.
- `pytest -q`: 79 passed, 2 skipped.
- Diagnostic attendance sessions were removed after verification.
