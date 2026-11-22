# Automatic Attendance Population and Confirmation

## Lifecycle

```
draft ──/process──▶ processing ──/image──▶ review_required ──/confirm──▶ confirmed
```

1. **Upload** (`POST /attendance/sessions/{id}/image`): the classroom photo goes through YuNet
   full-image and tiled detection, duplicate merging, quality checks, SFace embedding, and
   calibrated one-to-one matching (`MatchingService`). A session accepts **one** image; repeat
   uploads are rejected (422) before the CV pipeline runs.
2. **Proposed attendance** is built immediately, with one row per active roster student
   (table `proposed_attendance`):

   | Pipeline result | Proposed status | Recognition status |
   |---|---|---|
   | Confident, unique match (`matched_pending_review`) | `present` (checkbox pre-selected) | `matched` |
   | Best candidate of an ambiguous face | `needs_review` (never auto-present) | `ambiguous` |
   | Not found in the photo | `not_detected` (never auto-absent) | `not_detected` |

   Unknown and low-quality faces keep `student_id = NULL`; they are shown as face crops
   for manual identification.
3. **Review**: the reviewer can change present ↔ absent for any student, verify or reject an
   ambiguous identity, assign an unknown face to a student, or mark it "not a student". One
   student can never be assigned to two faces.
4. **Confirm** (`POST /attendance/sessions/{id}/confirm`): the session is validated (non-empty
   roster, no duplicate rows, no face claimed by two students, face/roster agreement). Then one
   transaction writes one `attendance_records` row per roster student:

   | Proposed | Final `attendance_status` | `verification_method` |
   |---|---|---|
   | present, auto | `present` | `face_recognition` |
   | present, face verified by reviewer | `present` | `manual_face_review` |
   | present, no face | `present` | `manual` |
   | absent | `absent` | `manual` |
   | needs_review / not_detected | **`unverified`** | `unresolved` |

   Any database error rolls back the whole confirmation (HTTP 500, nothing written) and the
   reviewer can retry. Confirming an already-confirmed session returns it unchanged
   (idempotent). `UNIQUE(session_id, student_id)` is enforced on both proposed and final tables.

## Classes / sections

Students have an optional `class_section` (e.g. `A`, `B`, `C`; up to 16 letters, digits or hyphens,
stored upper-case). A session created with `class_section` uses only that class's active students
as its roster and as the face-matching gallery, so students of other classes are never proposed,
assigned or confirmed in it. A session without a class covers all active students.

- `GET /students?class_section=B` filters the roster; `GET /students/classes` lists classes in use.
- `POST /attendance/sessions` accepts `class_section`; history, reports and exports include it.
- Roster CSV import reads an optional `class_section` (or `class`) column.

## API changes

| Method & path | Change |
|---|---|
| `POST /attendance/sessions/{id}/image` | Now returns the full session detail (superset of the old response): `attendance`, `summary`, `detections[].bbox`, `confirmation_problems`. |
| `GET /attendance/sessions/{id}` | Adds `attendance` (proposed rows; final records once confirmed), `summary`, `confirmed_by`. |
| `GET /attendance/sessions?status=` | **New.** Session history with present / absent / unverified counts. |
| `PUT /attendance/sessions/{id}/attendance/{student_id}` | **New.** Body `{status: "present"\|"absent", actor, notes}`. |
| `POST /attendance/sessions/{id}/confirm` | Accepts JSON `{actor}` (the `?actor=` query parameter still works). Idempotent; no longer requires every face to be reviewed first. |
| `GET /attendance/students/{id_or_usn}/history` | **New.** Per-student confirmed attendance and rate. |
| `GET /attendance/sessions/{id}/report?format=csv\|xlsx` | Adds `session_date`, `subject`, `verification_method`, `confirmed_at`, `confirmed_by`, and correction columns; status can be `unverified`. XLSX has a Summary sheet. |

## Database changes (additive, applied by `init_db`)

- New table `proposed_attendance`.
- `attendance_records`: `attendance_status`, `detection_row_id`, `verification_method`,
  `confirmed_at`, `reviewed_by`, `corrected_at`, `corrected_by`, `correction_reason`.
  Existing rows are backfilled from `present` and the session's `confirmed_at`.
- `attendance_sessions.confirmed_by`, `proposed_matches.candidate_student_id`.
- `students.class_section`, `attendance_sessions.class_section`.

## Enrollment on large photos

YuNet misses faces that fill a full-resolution phone portrait and fires on clothing patterns
instead. Photos whose longest side exceeds 1280 px are scanned at 1280, 960 and 640 px first; the
chosen box and landmarks are mapped back, and quality, alignment and embedding run on the
full-resolution image. Smaller photos use the original single pass.
