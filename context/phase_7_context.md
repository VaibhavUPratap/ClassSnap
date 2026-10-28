# Phase 7 Context — FastAPI REST API

## Status: COMPLETED

## Starting point
Phase 6 is complete with 63 passing tests. The API currently exposes health
and attendance session lifecycle endpoints under `/api/v1`.

## Existing API surface
- `GET /api/v1/health`
- `POST /api/v1/students`
- `GET /api/v1/students`
- `GET /api/v1/students/{student_id}`
- `PATCH /api/v1/students/{student_id}`
- `DELETE /api/v1/students/{student_id}`
- `POST /api/v1/students/import`
- `POST /api/v1/students/{student_id}/enrollment`
- `POST /api/v1/attendance/sessions/{session_id}/image`
- `POST /api/v1/attendance/sessions`
- `POST /api/v1/attendance/sessions/{session_id}/process`
- `POST /api/v1/attendance/sessions/{session_id}/proposals`
- `POST /api/v1/attendance/sessions/{session_id}/detections/{detection_id}/review`
- `POST /api/v1/attendance/sessions/{session_id}/confirm`
- `POST /api/v1/attendance/sessions/{session_id}/detections/{detection_id}/correction`

## Completed implementation
- Added roster CRUD and CSV import routes.
- Added consent-governed face enrollment upload route.
- Added classroom image processing route integrating CV detection,
  model-version-filtered roster embeddings, matching, and attendance
  proposals.
- Added shared image media-type, empty-upload, and maximum-size validation.
- Preserved structured domain error responses and added endpoint coverage.

## Validation
- Full test suite: 68 passed.
- One existing Starlette/httpx deprecation warning remains.

Phase 7 acceptance work is complete. Phase 8 is next.
