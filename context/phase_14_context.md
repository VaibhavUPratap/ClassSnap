# Phase 14: USN Validation Runtime Hardening

## Status

Completed on 2026-10-28.

## Root cause and fix

- Reproduced the served React page in a browser and inspected the live USN
  input: `pattern` was `null`, and `ENG24AM0107` was valid.
- Confirmed the previous browser wording could only come from a stale page or
  old API/schema validation path.
- Removed regex `pattern` metadata from the Pydantic schema.
- Replaced it with a custom validator that normalizes input and reports:
  `USN must use the format ENG24AM0107`.
- Disabled native form validation in React and kept explicit validation in the
  submit handler.
- Added Vite development proxying for `/api` to the FastAPI server.
- Disabled caching for the `/review/` HTML entrypoint.

## Validation

- `pytest -q`: 76 passed, 2 skipped.
- `cd frontend && npm run build`: passed.
- Browser inspection: `ENG24AM0107` has no pattern attribute and is valid.
- Live API: normalized lowercase/spaced USN accepted; invalid USN returns the
  custom validation message.
