# Phase 15: Student Removal Workflow

## Status

Completed on 2026-10-28.

## Delivered

- Added a Remove action to every active student row in the React dashboard.
- Added a confirmation prompt showing the student's name and USN.
- Connected the action to `DELETE /api/v1/students/{student_id}` using the
  student UUID and the web-admin actor.
- Updated the request helper to correctly handle the API's `204 No Content`
  response.
- Refreshes the roster and displays success or error feedback after removal.
- Added a danger-style button treatment for the destructive action.

## Validation

- `pytest -q`: 76 passed, 2 skipped.
- `cd frontend && npm run build`: passed.
- Live browser test: Remove action displayed, confirmation opened, DELETE was
  sent, and the student disappeared from the active roster.
