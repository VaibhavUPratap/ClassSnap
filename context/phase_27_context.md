# Phase 27: Correct Detection-to-Student Review Mapping

## Status

Completed on 2026-10-29.

## Delivered

- Attendance review responses now include proposed student name and USN.
- Review selectors synchronize with the candidate returned by the API.
- Overlapping detector boxes for one physical face are grouped before
  matching.
- When multiple aligned crops exist, the crop with the strongest roster
  similarity is selected instead of the highest raw detector confidence.
- Corrected Abhishek's active template using the left-person face from the
  supplied combined image.
- Live combined-image verification now produces exactly two proposals:
  Abhishek Hirmat and Vaibhav U Pratap.

## Validation

- Live API verification: two correct candidate assignments.
- Focused processing, attendance detail, and frontend tests passed.
- Frontend production build passed.
