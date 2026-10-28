# Phase 6 Context — Attendance Session Management and Database Workflow

## Status: COMPLETED

## Implemented so far
- Added SQLAlchemy models for attendance sessions, face detections,
  proposed matches, and final attendance records.
- Added session states: `draft`, `processing`, `review_required`, and
  `confirmed`.
- Added `AttendanceService` lifecycle methods for creating sessions,
  processing proposals, reviewing detections, and transactional confirmation.
- Added database uniqueness constraints for detections per session and
  students per confirmed session.
- Added guards preventing confirmation before all proposals are reviewed and
  preventing edits/repeated confirmation after confirmation.
- Added immutable `ReviewDecision` records capturing reviewer, decision,
  original candidate, selected student, notes, and timestamp.
- Added `correct_confirmed_attendance`, an audited correction path that
  preserves the confirmed session state, requires reviewer identity and
  reason, enforces session-student uniqueness, and records the before/after
  decision.
- Added rollback coverage proving a rejected duplicate correction leaves the
  finalized attendance set unchanged.
- Added cross-session transition coverage proving processing can only begin
  once, preventing duplicate processing submissions.
- Added versioned FastAPI endpoints for session creation, processing,
  proposals, human review, confirmation, and post-confirmation correction.
- Added initial tests for review gating, confirmation, uniqueness, and repeated
  confirmation, including review-decision persistence.

## Validation
- Full test suite: 63 passed.
- One existing Starlette/httpx deprecation warning remains.

Phase 6 acceptance criteria are complete. Phase 7 is next.
