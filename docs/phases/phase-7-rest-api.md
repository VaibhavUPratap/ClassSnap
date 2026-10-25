# Phase 7 — FastAPI REST API

## Goal
Expose business logic via versioned REST API.

## Required outputs
- `/api/v1` routes for roster, enrollment, sessions, processing, review, confirm, exports
- Request/response schemas and consistent error schema
- File upload validation (size, type, decode, dimensions, safety)
- Temp file lifecycle with cleanup and retention controls
- Authentication and role-based authorization
- OpenAPI docs via FastAPI
- Integration tests for happy path, invalid requests, auth failures, missing/conflicts

## Acceptance criteria
Documented routes enforce validation and authorization, and integration tests pass.
