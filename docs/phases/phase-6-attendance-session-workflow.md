# Phase 6 — Attendance Session Management and Database Workflow

## Goal
Implement attendance session lifecycle with transactional confirmation.

## Required outputs
- Models for sessions, detections, proposed matches, final attendance, review decisions, audits
- Session states: `draft`, `processing`, `review_required`, `confirmed`
- Lifecycle: create session → upload/process image → propose attendance → review/correct → confirm
- Session-student uniqueness constraints
- Transactional final confirmation and rollback safety
- Post-confirmation edit restrictions with defined correction workflow
- Tests for duplicate submissions, rollback, repeated confirmation, concurrency, and consistency

## Acceptance criteria
Attendance is consistent and auditable, unreviewed absences are not finalized, and confirmation is transactional.
