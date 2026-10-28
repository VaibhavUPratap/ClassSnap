# Phase 28: Attendance Confirmation and Reports Persistence

## Status

Completed on 2026-10-29.

## Findings

- Review decisions are stored immediately, but final attendance records are
  created only by the explicit confirmation step.
- Reports intentionally include only sessions with status `confirmed`.
- Recent sessions that were missing from Reports were still in
  `review_required`, including sessions where all detections had been
  reviewed but confirmation had not been completed.

## Delivered

- Attendance review UI now explicitly says that all detections must be
  confirmed before the session is stored in Reports.
- Confirmed sessions show that attendance is finalized and included in
  Reports.
- Added regression coverage proving reviewed-but-unconfirmed sessions are
  excluded from confirmed reports.

## Validation

- Focused attendance/report/frontend tests passed.
- Frontend production build passed.
