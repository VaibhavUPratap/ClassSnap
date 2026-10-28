# Phase 9 Context — Attendance Reports and Evaluation Framework

## Status: COMPLETED

## Starting point
Phase 8 is complete with 70 passing tests. Confirmed attendance records are
stored transactionally and the review workspace can confirm and correct them.

## Remaining work
- Add confirmed attendance report queries and CSV/XLSX exports.
- Add detection and matching evaluation summaries.
- Add report and export tests, including empty and corrected sessions.

## Implemented
- Added confirmed-session report generation with explicit present/absent rows
  for every active roster student.
- Added CSV and XLSX export service and API download endpoint.
- Reports are blocked until the session is confirmed.
- Added report service and API coverage.
- Added deterministic detection precision/recall/F1 evaluation summaries.
- Added identity matching outcome summaries that keep uncertain detections
  separate from accepted matches.

## Validation
- Full automated suite: 74 passed.
- One existing Starlette/httpx deprecation warning remains.

Phase 9 acceptance work is complete. Phase 10 is next.
