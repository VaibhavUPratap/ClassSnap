# ClassSnap

**Single-Image Classroom Attendance System** with Human-in-the-Loop Review.

ClassSnap is a modular, locally runnable computer vision and web application that identifies registered students from a single classroom photograph, presenting proposed attendance results for mandatory human review before confirmation.

---

## Architecture Overview

ClassSnap is designed around a layered architecture:
- **Presentation Layer**: Responsive web interface for upload, review, and attendance confirmation.
- **API Layer**: FastAPI versioned REST API (`/api/v1`).
- **Service Layer**: Business logic orchestrating student roster, face enrollment, tiled detection, identity matching, and attendance sessions.
- **Computer Vision Engine**: Pluggable interfaces for face detection (`YuNet`), face alignment, and normalized embedding extraction (`SFace`).
- **Persistence Layer**: SQLite with SQLAlchemy ORM, managing transactional confirmation and audit logging.
- **Reporting Layer**: Confirmed attendance exports in CSV and Excel formats.

---

## Project Structure

```text
ClassSnap/
├── classsnap/                 # Core application package
│   ├── api/                   # REST API routes and endpoints
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py  # Health check endpoint
│   │       └── router.py      # v1 router aggregator
│   ├── cv/                    # Computer vision engine (detector, embedder)
│   ├── db/                    # Database session and base models
│   │   ├── base.py
│   │   └── session.py
│   ├── models/                # SQLAlchemy ORM database models
│   ├── schemas/               # Pydantic request/response schemas
│   │   └── health.py
│   ├── services/              # Business domain services
│   ├── config.py              # Centralized pydantic-settings configuration
│   ├── exceptions.py          # Domain exceptions & error handlers
│   ├── logger.py              # Structured logging configuration
│   └── main.py                # FastAPI entry point & lifespan manager
├── context/                   # Context management & state tracking
│   ├── system_state.json      # Machine-readable phase & system state
│   ├── retrieve_context.py    # Automated context retrieval utility
│   ├── phase_0_context.md     # Architecture & requirements summary
│   └── phase_1_context.md     # Phase 1 foundation documentation
├── docs/                      # Phase-by-phase specifications
├── tests/                     # Automated test suite
│   ├── conftest.py            # Test fixtures & in-memory database setup
│   ├── test_app.py            # Application startup & routes tests
│   ├── test_config.py         # Configuration & environment variable tests
│   ├── test_db.py             # Database connectivity & session tests
│   ├── test_exceptions.py     # Custom exception handling tests
│   └── test_health.py         # Health check endpoint tests
├── .env.example               # Example environment variable file
├── .gitignore                 # Sensitive file & biometric data exclusions
├── pyproject.toml             # Project build & dependency metadata
├── pytest.ini                 # Pytest runner configuration
├── requirements.txt           # Production dependencies
└── requirements-dev.txt       # Development & testing dependencies
```

---

## Setup Instructions (macOS / Linux)

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- `pip` and `virtualenv`

### 2. Environment Setup
Create and activate a virtual environment:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
# Install core dependencies
pip install -r requirements.txt

# Or install development dependencies including test runner
pip install -r requirements-dev.txt
```

### 4. Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```
Adjust parameters in `.env` as required (database path, model locations, log level).

---

## Running the Application

Start the local development server with Uvicorn:

```bash
# Using uvicorn directly
uvicorn classsnap.main:app --host 127.0.0.1 --port 8000 --reload

# Or using Python module execution
python -m classsnap.main
```

Once running:
- **API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative API Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## Running the Test Suite

Execute automated tests with `pytest`:

```bash
# Run all tests with verbose output
pytest

# Run a specific test module
pytest tests/test_health.py
```

---

## Context Retrieval

ClassSnap includes an automated context tracker in `context/`:
```bash
# Print current state, active phase, and architectural guidelines
python3 context/retrieve_context.py
```
