# Phase 17: Roster Response Serialization Fix

## Status

Completed on 2026-10-28.

## Root cause

`GET /api/v1/students` returned HTTP 500 for students with enrolled face
templates. The response schema accepted `FaceTemplateSummary` dictionaries but
not SQLAlchemy `FaceTemplate` ORM objects. The failure was surfaced as a
backend validation error during roster loading.

## Delivered

- Added `ConfigDict(from_attributes=True)` to `FaceTemplateSummary`.
- Kept the response schema independent from strict student-input USN validation,
  so legacy records can still be listed and removed.
- Added a regression test for listing legacy non-USN records.

## Validation

- `pytest -q`: 77 passed, 2 skipped.
- `python3 -m compileall -q classsnap`: passed.
- Fresh Uvicorn server: health and roster endpoints returned successfully.
- Verified a roster response containing enrolled face templates.
