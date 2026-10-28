# Phase 13: USN Student ID Validation

## Status

Completed on 2026-10-28.

## Delivered

- Student IDs are now validated as USNs matching
  `^[A-Z]{3}[0-9]{2}[A-Z]{2}[0-9]{4}$`.
- Example accepted USN: `ENG24AM0107`.
- The FastAPI student schema rejects invalid IDs with HTTP 422.
- CSV roster imports reject invalid USNs with row-level error details.
- The React student form labels the field as USN and provides browser validation,
  placeholder text, and format guidance.
- Updated existing test fixtures to use valid USNs.
- Added explicit API coverage for valid and invalid USN values.

## Validation

- `pytest -q`: 75 passed, 2 skipped.
- `cd frontend && npm run build`: passed.
- `python3 -m compileall -q classsnap`: passed.
- `git diff --check`: passed.
