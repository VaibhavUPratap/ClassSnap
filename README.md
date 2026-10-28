# ClassSnap

ClassSnap is a locally runnable, single-image classroom attendance system
with computer vision and mandatory human review. It detects faces in a
classroom photograph, proposes identities from a consented roster, and
requires a reviewer to approve attendance before it is finalized.

The project includes both:

- A FastAPI backend and REST API under `/api/v1`
- A dependency-free browser frontend served at `/review/`

## Features

- OpenCV YuNet face detection
- OpenCV SFace 128-dimensional face embeddings
- Full-image and overlapping tiled detection for high-resolution photos
- Quality checks, normalized embeddings, and model-version compatibility
- Deterministic identity matching with explicit uncertainty statuses
- Consent-based face enrollment with audit logging
- One-to-one identity assignment to prevent duplicate matches
- Transactional attendance sessions with review and correction workflows
- CSV and XLSX attendance exports
- Detection and matching evaluation summaries
- Upload media-type, size, and empty-file validation
- Local processing with temporary photo non-retention by default

## Architecture

```text
Browser review workspace (/review/)
              |
              v
Versioned FastAPI API (/api/v1)
              |
              v
Domain services
  - roster and consent
  - face enrollment
  - CV processing and matching
  - attendance sessions and review
  - reporting and evaluation
              |
              v
OpenCV CV engine + SQLAlchemy persistence
```

### Main directories

```text
classsnap/
├── api/v1/                  # FastAPI routers and endpoints
├── cv/                      # Detection, alignment, embedding, quality, tiling
├── db/                      # SQLAlchemy base and database sessions
├── models/                  # Roster, biometric, audit, and attendance models
├── schemas/                 # Pydantic API schemas
├── services/                # Application and domain services
├── web/                     # Browser review workspace
├── config.py                # Environment-backed settings
└── main.py                  # FastAPI application entry point
context/                     # Phase state and continuation context
docs/                        # Phase specifications
eval/                        # Non-biometric benchmark metadata
models/                      # YuNet and SFace ONNX model files
scripts/                     # Model, CV demo, and evaluation utilities
tests/                       # Automated test suite
```

## Requirements

- Python 3.10 or newer
- `pip`
- A local environment capable of running OpenCV

The project has been validated with Python 3.14.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Copy the example configuration if you need local overrides:

```bash
cp .env.example .env
```

Never commit `.env`, real student photographs, biometric data, or generated
attendance exports. Production requires a unique `SECRET_KEY` of at least
32 characters and rejects debug mode.

## Run the application

Start the development server:

```bash
uvicorn classsnap.main:app --host 127.0.0.1 --port 8000 --reload
```

Or:

```bash
python -m classsnap.main
```

### Browser frontend

Open the review workspace at:

```text
http://127.0.0.1:8000/review/
```

The frontend files are in `classsnap/web/` and are served directly by FastAPI;
it is not a separate React,
Vue, or Next.js application. It provides:

1. Attendance session creation
2. Classroom image upload
3. Face detection and identity proposal processing
4. Proposal review with present/absent decisions
5. Candidate student ID entry
6. Attendance confirmation
7. Post-confirmation correction through the audited workflow
8. Status and privacy messaging

### API documentation

When the server is running:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Health check: <http://127.0.0.1:8000/api/v1/health>

## API surface

### Roster and enrollment

```text
POST   /api/v1/students
GET    /api/v1/students
GET    /api/v1/students/{student_id}
PATCH  /api/v1/students/{student_id}
DELETE /api/v1/students/{student_id}
POST   /api/v1/students/import
POST   /api/v1/students/{student_id}/enrollment
```

### Attendance workflow

```text
POST /api/v1/attendance/sessions
GET  /api/v1/attendance/sessions/{session_id}
POST /api/v1/attendance/sessions/{session_id}/process
POST /api/v1/attendance/sessions/{session_id}/image
POST /api/v1/attendance/sessions/{session_id}/proposals
POST /api/v1/attendance/sessions/{session_id}/detections/{detection_id}/review
POST /api/v1/attendance/sessions/{session_id}/confirm
POST /api/v1/attendance/sessions/{session_id}/detections/{detection_id}/correction
GET  /api/v1/attendance/sessions/{session_id}/report?format=csv
GET  /api/v1/attendance/sessions/{session_id}/report?format=xlsx
```

Attendance confirmation is blocked until every proposed detection has been
reviewed. Corrections after confirmation require a reviewer identity and
reason and are recorded as audit events.

## Privacy and security

- Face enrollment requires recorded consent.
- Images are processed in memory by default.
- Temporary enrollment photos are deleted according to the configured
  retention policy.
- Uploads must use an image media type and remain within the configured
  maximum size.
- `.env`, databases, uploads, biometric directories, and generated exports
  are ignored by Git.
- Production rejects the development secret key and `DEBUG=true`.
- CORS origins are explicit through `CORS_ALLOWED_ORIGINS`.
- Uncertain matches remain unassigned until a human reviews them.

## Run tests

Run the complete suite:

```bash
pytest -q
```

Run a focused test module:

```bash
pytest -q tests/test_attendance_service.py
```

The current repository validation result is:

```text
74 passed, 2 skipped
```

The skipped tests require a local face photograph. Real biometric image
fixtures are intentionally not committed to the repository.

## CV demo

Provide your own local image explicitly:

```bash
python scripts/run_cv_demo.py /path/to/local/classroom.jpg \
  --output /tmp/classsnap-annotated.jpg
```

The demo prints detections, quality, confidence, and embedding dimensions.
Do not point it at real student data unless you have the required consent and
privacy controls.

## Context tracking

The repository includes a machine-readable phase tracker:

```bash
python3 context/retrieve_context.py
```

The current project context is stored in
[context/system_state.json](context/system_state.json), with detailed
continuation notes in `context/phase_*_context.md`.
