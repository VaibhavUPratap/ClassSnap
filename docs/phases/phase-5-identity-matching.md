# Phase 5 — Identity Matching and Uncertainty Handling

## Goal
Build deterministic matching with explicit uncertainty statuses.

## Required outputs
- Matching service with normalized embeddings and similarity ranking
- Threshold configuration for accept/ambiguity and separation margin
- Calibration utility using consented labeled classroom data
- Statuses: `matched_pending_review`, `unknown`, `low_quality`, `ambiguous`, `no_candidate`
- Duplicate identity prevention with one-to-one assignment + rejection option
- Structured match result schema with scores and rejection reasons
- Tests for known/unknown/ambiguous/low-quality/duplicate/empty-roster/version mismatch paths

## Acceptance criteria
Matching is deterministic, uncertain detections stay unassigned, duplicate assignments are prevented, and threshold edges are covered by tests.
