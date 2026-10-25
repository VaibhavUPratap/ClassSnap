# Phase 4 — Student Roster and Face Enrollment

## Goal
Implement secure roster management and consent-based enrollment.

## Required outputs
- Student and face-template models
- CSV roster import with validation and duplicate handling
- CRUD/deactivation for students
- Enrollment upload and single-face validation
- Embedding extraction + model-version metadata tracking
- Multiple references per student and baseline aggregation support
- Consent/authorization metadata requirements
- Default non-retention of originals unless explicitly configured
- Tests for invalid images, multiple faces, duplicates, missing consent, version mismatch, deletion flows

## Acceptance criteria
Valid roster import and enrollment succeed, references are retrievable, and invalid/unauthorized enrollment is rejected.
