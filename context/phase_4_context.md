# Phase 4 Context — Student Roster and Face Enrollment

## Status: COMPLETED

## Deliverables
1. **ORM Models** (`classsnap/models/`):
   - `Student`: UUID PK, student_id (unique), name, email, is_active, has_consent, consent_recorded_at, consent_notes. Safe `__init__` ensures id is pre-set before any audit reference.
   - `FaceTemplate`: UUID PK, FK → Student, model_name, model_version, embedding_dim, embedding_blob (binary float32), quality_score, sharpness, is_primary.
   - `AuditEvent`: UUID PK, action, entity_type, entity_id, actor, details.
2. **RosterService** (`classsnap/services/roster_service.py`):
   - `create_student` with duplicate check + audit flush-before-log pattern.
   - `get_student_by_id` by UUID or institutional ID.
   - `update_student` with consent timestamp management.
   - `deactivate_student` (soft delete).
   - `delete_student` (hard delete, cascades templates).
   - `import_roster_from_csv`: UTF-8-sig/Latin-1 encoding support, header normalization, duplicate detection within CSV and DB, row-level error reporting.
3. **EnrollmentService** (`classsnap/services/enrollment_service.py`):
   - Consent pre-check + inline consent grant at enrollment time.
   - Single-face validation: rejects 0 or >1 detected faces.
   - Face quality gate: rejects low-sharpness/small faces.
   - L2-normalized 128D SFace embedding extraction + binary blob storage.
   - `get_aggregated_student_embedding`: averages all templates and renormalizes (enables multi-reference matching).
   - Model version filtering to prevent cross-version comparisons.
   - `delete_template` and `delete_all_student_templates` with audit logging.
   - Auto photo non-retention (purges temp uploads after processing).
4. **Pydantic Schemas**: `StudentCreate/Update/Response`, `FaceTemplateSummary`, `RosterImportSummary/Error`, `EnrollmentConsentPayload/Response`.
5. **Test Suite**: 20 tests across roster and enrollment service (7 + 13), all passing. 51 total tests.
