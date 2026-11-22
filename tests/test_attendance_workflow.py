"""End-to-end tests for automatic attendance population and confirmation.

Every test runs against its own throwaway SQLite *file* database (pytest's
``tmp_path``), never the application's configured database. Each HTTP request
gets a fresh SQLAlchemy session, so reading a session back after confirmation
really exercises what was committed to disk.

The CV models are replaced with a deterministic fake engine so the test can
control exactly which faces match which enrolled students; the real matching,
de-duplication, persistence and confirmation code runs unmodified.
"""

import csv
import io
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from classsnap.cv.engine import CVEngine
from classsnap.cv.types import BoundingBox, DetectionResult, FaceQuality
from classsnap.db.session import get_db, init_db
from classsnap.main import create_app
from classsnap.models.attendance import (
    AttendanceDetection,
    AttendanceRecord,
    AttendanceSession,
    ProposedAttendance,
)
from classsnap.models.student import Student
from classsnap.services import attendance_service as attendance_module
from classsnap.services.enrollment_service import EnrollmentService

DIM = 8
REVIEWER = "teacher-qa"


def _unit(*weights: float) -> np.ndarray:
    vector = np.zeros(DIM, dtype=np.float32)
    vector[: len(weights)] = weights
    return vector / np.linalg.norm(vector)


E = [_unit(*([0.0] * i + [1.0])) for i in range(DIM)]

# Enrolled references (by USN).
REFERENCES = {
    "WRK24AT0001": E[0],                     # Ada    – clearly matched
    "WRK24AT0002": E[1],                     # Grace  – clearly matched
    "WRK24AT0003": E[2],                     # Kathy  – ambiguous with Dorothy
    "WRK24AT0004": _unit(0, 0, 0.99, 0.14),  # Dorothy – near-duplicate of Kathy
    "WRK24AT0005": E[4],                     # Alan   – not in the photo
}
NAMES = {
    "WRK24AT0001": ("Ada", "Lovelace"),
    "WRK24AT0002": ("Grace", "Hopper"),
    "WRK24AT0003": ("Katherine", "Johnson"),
    "WRK24AT0004": ("Dorothy", "Vaughan"),
    "WRK24AT0005": ("Alan", "Turing"),
}


def _face(index: int, embedding, usable: bool = True) -> DetectionResult:
    # Boxes are far apart so de-duplication keeps every face.
    return DetectionResult(
        bbox=BoundingBox(40 + index * 400, 60, 120, 120),
        confidence=0.95,
        quality=FaceQuality(is_usable=usable, rejection_reason=None if usable else "blurred"),
        embedding=None if embedding is None else [float(v) for v in embedding],
        detection_id=f"face-{index}",
    )


def _classroom_faces() -> list[DetectionResult]:
    return [
        _face(0, E[0]),            # Ada
        _face(1, E[1]),            # Grace
        _face(2, E[2]),            # Kathy vs Dorothy → ambiguous, must not auto-assign
        _face(3, E[6]),            # stranger → unknown
        _face(4, E[7], usable=False),  # low quality → unknown
    ]


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'isolated-attendance.db'}",
        connect_args={"check_same_thread": False},
    )
    init_db(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    app = create_app()

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    faces = {"value": _classroom_faces()}
    fake_engine = SimpleNamespace(
        embedder=SimpleNamespace(model_version="test-sface"),
        process_image=lambda image, **kwargs: (list(faces["value"]), image),
    )
    monkeypatch.setattr(CVEngine, "from_settings", classmethod(lambda cls: fake_engine))

    with TestClient(app) as client:
        ids = {}
        for usn, (first, last) in NAMES.items():
            response = client.post(
                "/api/v1/students",
                json={"student_id": usn, "first_name": first, "last_name": last},
            )
            assert response.status_code == 201, response.text
            ids[usn] = response.json()["id"]
        by_pk = {pk: usn for usn, pk in ids.items()}

        def aggregated(db, student_pk, required_model_version=None):
            return REFERENCES[by_pk[student_pk]]

        monkeypatch.setattr(
            EnrollmentService, "get_aggregated_student_embedding", staticmethod(aggregated)
        )
        yield SimpleNamespace(
            client=client, Session=Session, engine=engine, ids=ids, faces=faces
        )
    app.dependency_overrides.clear()
    engine.dispose()


def _process(env, name="CS 401 · Lecture 4", class_at="2026-11-20T09:00:00"):
    client = env.client
    created = client.post(
        "/api/v1/attendance/sessions",
        json={"name": name, "class_at": class_at, "actor": REVIEWER},
    )
    session_id = created.json()["id"]
    assert client.post(f"/api/v1/attendance/sessions/{session_id}/process").status_code == 200
    processed = client.post(
        f"/api/v1/attendance/sessions/{session_id}/image",
        files={"image": ("classroom.jpg", b"jpeg-bytes", "image/jpeg")},
    )
    assert processed.status_code == 200, processed.text
    return session_id, processed.json()


def _by_usn(detail):
    return {entry["student_usn"]: entry for entry in detail["attendance"]}


def _confirm(env, session_id):
    return env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/confirm", json={"actor": REVIEWER}
    )


# 1, 2, 3, 4, 5 -----------------------------------------------------------------


def test_upload_auto_marks_recognized_students_present(env):
    session_id, detail = _process(env)
    rows = _by_usn(detail)

    assert detail["status"] == "review_required"
    # Recognized and uniquely matched → PRESENT with no manual action.
    for usn in ("WRK24AT0001", "WRK24AT0002"):
        assert rows[usn]["status"] == "present"
        assert rows[usn]["recognition_status"] == "matched"
        assert rows[usn]["detection_id"] is not None
        assert rows[usn]["manually_set"] is False
    assert rows["WRK24AT0001"]["detection_id"] == "face-0"
    assert rows["WRK24AT0002"]["detection_id"] == "face-1"

    # Ambiguous match → flagged for review, never auto-present.
    assert rows["WRK24AT0003"]["status"] == "needs_review"
    assert rows["WRK24AT0003"]["detection_id"] == "face-2"
    # Undetected students are NOT auto-absent.
    assert rows["WRK24AT0004"]["status"] == "not_detected"
    assert rows["WRK24AT0005"]["status"] == "not_detected"

    # Unknown faces stay unassigned; no arbitrary names.
    faces = {d["detection_id"]: d for d in detail["detections"]}
    for face_id in ("face-2", "face-3", "face-4"):
        assert faces[face_id]["student_id"] is None
    assert faces["face-2"]["candidate_student_name"] == "Katherine Johnson"
    assert faces["face-0"]["bbox"]["w"] == 120

    assert detail["summary"] == {
        "total_registered": 5,
        "auto_identified": 2,
        "proposed_present": 2,
        "proposed_absent": 0,
        "needs_review": 1,
        "not_detected": 2,
        "unknown_faces": 3,
        "faces_detected": 5,
        "manually_corrected": 0,
    }
    assert detail["confirmation_problems"] == []

    # The proposal is persisted, not just echoed back.
    reloaded = env.client.get(f"/api/v1/attendance/sessions/{session_id}").json()
    assert _by_usn(reloaded)["WRK24AT0001"]["status"] == "present"
    with env.Session() as db:
        assert db.query(AttendanceRecord).count() == 0  # nothing final yet
        assert db.query(ProposedAttendance).filter_by(session_id=session_id).count() == 5


# 6, 7, 8 ------------------------------------------------------------------------


def test_manual_corrections_then_confirm_persists_across_restart(env, tmp_path):
    session_id, _ = _process(env)
    client, ids = env.client, env.ids

    # Resolve the ambiguous face as Kathy.
    reviewed = client.post(
        f"/api/v1/attendance/sessions/{session_id}/detections/face-2/review",
        json={"present": True, "student_id": ids["WRK24AT0003"], "actor": REVIEWER},
    )
    assert reviewed.status_code == 200, reviewed.text
    # Grace was misidentified → mark absent (releases her face).
    response = client.put(
        f"/api/v1/attendance/sessions/{session_id}/attendance/{ids['WRK24AT0002']}",
        json={"status": "absent", "actor": REVIEWER, "notes": "Not in class"},
    )
    assert response.status_code == 200, response.text
    # Alan was present but not detected → mark present manually.
    detail = client.put(
        f"/api/v1/attendance/sessions/{session_id}/attendance/{ids['WRK24AT0005']}",
        json={"status": "present", "actor": REVIEWER},
    ).json()
    rows = _by_usn(detail)
    assert rows["WRK24AT0003"]["status"] == "present"
    assert rows["WRK24AT0002"]["status"] == "absent"
    assert rows["WRK24AT0002"]["detection_id"] is None
    assert rows["WRK24AT0005"]["status"] == "present"
    assert detail["summary"]["manually_corrected"] == 3
    faces = {d["detection_id"]: d for d in detail["detections"]}
    assert faces["face-1"]["student_id"] is None  # released, not silently kept

    confirmed = _confirm(env, session_id)
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "confirmed"
    assert body["confirmed_by"] == REVIEWER

    # Simulate an application restart: brand-new engine on the same file.
    db_path = env.engine.url.database
    env.engine.dispose()
    fresh = create_engine(f"sqlite:///{db_path}")
    init_db(fresh)
    with sessionmaker(bind=fresh)() as db:
        session = db.get(AttendanceSession, session_id)
        assert session.status == "confirmed"
        assert session.confirmed_by == REVIEWER and session.confirmed_at is not None
        records = {
            db.get(Student, r.student_id).student_id: r
            for r in db.execute(
                select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
            ).scalars()
        }
    fresh.dispose()
    assert {usn: r.attendance_status for usn, r in records.items()} == {
        "WRK24AT0001": "present",
        "WRK24AT0002": "absent",
        "WRK24AT0003": "present",
        "WRK24AT0004": "unverified",  # never silently converted to absent
        "WRK24AT0005": "present",
    }
    assert records["WRK24AT0001"].verification_method == "face_recognition"
    assert records["WRK24AT0001"].detection_row_id is not None
    assert records["WRK24AT0003"].verification_method == "manual_face_review"
    assert records["WRK24AT0005"].verification_method == "manual"
    assert records["WRK24AT0004"].verification_method == "unresolved"
    assert all(r.reviewed_by == REVIEWER and r.confirmed_at for r in records.values())

    # Reload through the API ("refresh the page").
    reloaded = env.client.get(f"/api/v1/attendance/sessions/{session_id}").json()
    assert reloaded["status"] == "confirmed"
    assert reloaded["summary"]["present"] == 3
    assert reloaded["summary"]["absent"] == 1
    assert reloaded["summary"]["unverified"] == 1
    assert _by_usn(reloaded)["WRK24AT0001"]["attendance_id"] == records["WRK24AT0001"].id


def test_duplicate_identity_assignment_is_rejected(env):
    session_id, _ = _process(env)
    # Assigning Ada (already face-0) to another face must fail.
    response = env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/detections/face-3/review",
        json={"present": True, "student_id": env.ids["WRK24AT0001"], "actor": REVIEWER},
    )
    assert response.status_code == 422
    assert "already assigned" in response.json()["error"]["message"]


def test_confirm_blocked_by_invalid_identity_then_retry_succeeds(env):
    session_id, _ = _process(env)
    # Corrupt the proposal: two faces claim the same student.
    with env.Session() as db:
        face = db.execute(
            select(AttendanceDetection).where(
                AttendanceDetection.session_id == session_id,
                AttendanceDetection.detection_id == "face-3",
            )
        ).scalar_one()
        face.proposed_match.student_id = env.ids["WRK24AT0001"]
        db.commit()

    blocked = _confirm(env, session_id)
    assert blocked.status_code == 422
    assert blocked.json()["error"]["details"]["problems"]
    with env.Session() as db:
        assert db.get(AttendanceSession, session_id).status == "review_required"
        assert db.query(AttendanceRecord).count() == 0

    # Correct it and retry.
    env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/detections/face-3/review",
        json={"present": False, "actor": REVIEWER, "notes": "Stranger"},
    )
    assert _confirm(env, session_id).status_code == 200


# 9, 10 ----------------------------------------------------------------------------


def test_history_and_exports_match_database(env):
    session_id, _ = _process(env)
    assert _confirm(env, session_id).status_code == 200

    history = env.client.get("/api/v1/attendance/sessions?status=confirmed").json()
    entry = next(item for item in history if item["session_id"] == session_id)
    assert entry["present_count"] == 2
    assert entry["absent_count"] == 0
    assert entry["unverified_count"] == 3
    assert entry["total_registered"] == 5
    assert entry["confirmed_by"] == REVIEWER

    with env.Session() as db:
        expected = {
            db.get(Student, r.student_id).student_id: r.attendance_status
            for r in db.execute(
                select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
            ).scalars()
        }

    csv_response = env.client.get(f"/api/v1/attendance/sessions/{session_id}/report?format=csv")
    assert csv_response.status_code == 200
    csv_rows = list(csv.DictReader(io.StringIO(csv_response.text)))
    assert {row["student_id"]: row["status"] for row in csv_rows} == expected
    first = csv_rows[0]
    assert first["subject"] == "CS 401 · Lecture 4"
    assert first["session_date"] == "2026-11-20"
    assert first["confirmed_by"] == REVIEWER and first["confirmed_at"]
    assert {row["student_name"] for row in csv_rows} >= {"Ada Lovelace", "Grace Hopper"}

    xlsx_response = env.client.get(f"/api/v1/attendance/sessions/{session_id}/report?format=xlsx")
    sheet = load_workbook(io.BytesIO(xlsx_response.content))["Attendance"]
    header, *data = list(sheet.iter_rows(values_only=True))
    index = {name: i for i, name in enumerate(header)}
    assert {r[index["student_id"]]: r[index["status"]] for r in data} == expected


# 11 -------------------------------------------------------------------------------


def test_double_confirmation_and_repeat_upload_create_no_duplicates(env):
    session_id, _ = _process(env)
    first = _confirm(env, session_id)
    second = _confirm(env, session_id)
    assert first.status_code == second.status_code == 200
    assert first.json()["confirmed_at"] == second.json()["confirmed_at"]

    repeat = env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/image",
        files={"image": ("classroom.jpg", b"jpeg-bytes", "image/jpeg")},
    )
    assert repeat.status_code == 422
    with env.Session() as db:
        assert db.query(AttendanceRecord).filter_by(session_id=session_id).count() == 5
        assert db.query(AttendanceDetection).filter_by(session_id=session_id).count() == 5

        # The database itself refuses a second record for the same student.
        existing = db.execute(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
        ).scalars().first()
        db.add(
            AttendanceRecord(
                session_id=session_id,
                student_id=existing.student_id,
                present=True,
                attendance_status="present",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


# 12 -------------------------------------------------------------------------------


def test_database_failure_rolls_back_entire_confirmation(env, monkeypatch):
    session_id, _ = _process(env)
    real_record = attendance_module.AttendanceRecord
    calls = {"n": 0}

    def failing_record(**kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            kwargs["student_id"] = None  # NOT NULL violation mid-transaction
        return real_record(**kwargs)

    monkeypatch.setattr(attendance_module, "AttendanceRecord", failing_record)
    failed = _confirm(env, session_id)
    assert failed.status_code == 500
    assert "No records were changed" in failed.json()["error"]["message"]

    with env.Session() as db:
        assert db.get(AttendanceSession, session_id).status == "review_required"
        assert db.query(AttendanceRecord).count() == 0
        assert db.query(ProposedAttendance).filter_by(session_id=session_id).count() == 5

    monkeypatch.setattr(attendance_module, "AttendanceRecord", real_record)
    retried = _confirm(env, session_id)
    assert retried.status_code == 200
    assert retried.json()["summary"]["present"] == 2


# 13 -------------------------------------------------------------------------------


def test_sessions_store_attendance_independently_and_student_history(env):
    first_id, _ = _process(env, name="Monday", class_at="2026-11-16T09:00:00")
    env.faces["value"] = [_face(0, E[0])]  # only Ada attends Tuesday
    second_id, detail = _process(env, name="Tuesday", class_at="2026-11-17T09:00:00")
    assert _by_usn(detail)["WRK24AT0002"]["status"] == "not_detected"
    env.client.put(
        f"/api/v1/attendance/sessions/{second_id}/attendance/{env.ids['WRK24AT0002']}",
        json={"status": "absent", "actor": REVIEWER},
    )
    assert _confirm(env, first_id).status_code == 200
    assert _confirm(env, second_id).status_code == 200

    first = _by_usn(env.client.get(f"/api/v1/attendance/sessions/{first_id}").json())
    second = _by_usn(env.client.get(f"/api/v1/attendance/sessions/{second_id}").json())
    assert first["WRK24AT0002"]["status"] == "present"
    assert second["WRK24AT0002"]["status"] == "absent"

    ada = env.client.get("/api/v1/attendance/students/WRK24AT0001/history").json()
    assert ada["total_sessions"] == 2 and ada["sessions_attended"] == 2
    grace = env.client.get(
        f"/api/v1/attendance/students/{env.ids['WRK24AT0002']}/history"
    ).json()
    assert grace["sessions_attended"] == 1
    assert grace["sessions_absent"] == 1
    assert grace["attendance_rate"] == 0.5
    assert [s["session_name"] for s in grace["sessions"]] == ["Tuesday", "Monday"]


# Migration ------------------------------------------------------------------------


def test_init_db_migrates_legacy_attendance_records(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    Student.__table__.create(engine)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE attendance_sessions (id VARCHAR(36) PRIMARY KEY, name VARCHAR(255) NOT NULL, "
            "status VARCHAR(32) NOT NULL, created_by VARCHAR(100) NOT NULL, class_at DATETIME, "
            "confirmed_at DATETIME, created_at DATETIME NOT NULL)"
        ))
        conn.execute(text(
            "CREATE TABLE attendance_records (id VARCHAR(36) PRIMARY KEY, session_id VARCHAR(36) NOT NULL, "
            "student_id VARCHAR(36) NOT NULL, present BOOLEAN NOT NULL, source VARCHAR(32) NOT NULL, "
            "created_at DATETIME NOT NULL, CONSTRAINT uq_session_student_attendance UNIQUE (session_id, student_id))"
        ))
        for pk, usn in (("s1", "LEG24AT0001"), ("s2", "LEG24AT0002")):
            conn.execute(text(
                "INSERT INTO students (id, student_id, first_name, last_name, is_active, has_consent, created_at) "
                f"VALUES ('{pk}', '{usn}', 'Legacy', '{usn}', 1, 0, '2026-01-01')"
            ))
        conn.execute(text(
            "INSERT INTO attendance_sessions VALUES "
            "('sess', 'Legacy class', 'confirmed', 'teacher', '2026-01-05', '2026-01-05 10:00:00', '2026-01-05')"
        ))
        conn.execute(text(
            "INSERT INTO attendance_records VALUES ('r1', 'sess', 's1', 1, 'review', '2026-01-05'), "
            "('r2', 'sess', 's2', 0, 'review', '2026-01-05')"
        ))

    init_db(engine)

    with sessionmaker(bind=engine)() as db:
        statuses = {r.id: r.attendance_status for r in db.query(AttendanceRecord)}
        assert statuses == {"r1": "present", "r2": "absent"}
        assert db.get(AttendanceRecord, "r1").confirmed_at is not None
        from classsnap.services.report_service import ReportService

        summary = ReportService.confirmed_sessions(db)
        assert summary.sessions[0].present_count == 1
        assert summary.sessions[0].absent_count == 1
    engine.dispose()


# Multiple photos per session -------------------------------------------------------


def _photo_engine(monkeypatch, photos):
    """Fake engine whose faces depend on which photo (by its bytes) is processed."""
    fake_engine = SimpleNamespace(
        embedder=SimpleNamespace(model_version="test-sface"),
        process_image=lambda image, **kwargs: (list(photos[image]), image),
    )
    monkeypatch.setattr(CVEngine, "from_settings", classmethod(lambda cls: fake_engine))


def _new_session(env):
    created = env.client.post(
        "/api/v1/attendance/sessions",
        json={"name": "Multi-photo lecture", "class_at": "2026-11-21T09:00:00", "actor": REVIEWER},
    )
    session_id = created.json()["id"]
    assert env.client.post(f"/api/v1/attendance/sessions/{session_id}/process").status_code == 200
    return session_id


def test_several_photos_in_one_upload_mark_each_student_present_once(env, monkeypatch):
    _photo_engine(
        monkeypatch,
        {
            b"front": [_face(0, E[0]), _face(1, E[6])],  # Ada + a stranger
            b"back": [_face(0, E[1]), _face(1, E[0])],   # Grace + Ada again
        },
    )
    session_id = _new_session(env)
    response = env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/images",
        files=[
            ("images", ("front.jpg", b"front", "image/jpeg")),
            ("images", ("back.jpg", b"back", "image/jpeg")),
        ],
    )
    assert response.status_code == 200, response.text
    detail = response.json()
    rows = _by_usn(detail)

    assert detail["photo_count"] == 2
    assert sorted(d["photo_index"] for d in detail["detections"]) == [1, 1, 2, 2]
    assert len({d["detection_id"] for d in detail["detections"]}) == 4
    assert rows["WRK24AT0001"]["status"] == "present"  # Ada, seen in both photos
    assert rows["WRK24AT0002"]["status"] == "present"  # Grace, back photo only
    assert rows["WRK24AT0005"]["status"] == "not_detected"
    assert detail["summary"]["proposed_present"] == 2
    assert detail["confirmation_problems"] == []

    confirmed = _confirm(env, session_id)
    assert confirmed.status_code == 200, confirmed.text
    final = _by_usn(confirmed.json())
    assert final["WRK24AT0001"]["status"] == "present"
    assert final["WRK24AT0002"]["status"] == "present"
    with env.Session() as db:
        assert db.query(AttendanceRecord).filter_by(session_id=session_id).count() == 5


def test_photo_added_during_review_updates_only_untouched_rows(env, monkeypatch):
    _photo_engine(
        monkeypatch,
        {
            b"first": [_face(0, E[0])],                 # Ada
            b"second": [_face(0, E[1]), _face(1, E[4])],  # Grace + Alan
        },
    )
    session_id = _new_session(env)
    first = env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/image",
        files={"image": ("first.jpg", b"first", "image/jpeg")},
    )
    assert first.status_code == 200, first.text
    assert first.json()["photo_count"] == 1
    grace_pk = env.ids["WRK24AT0002"]
    # The reviewer explicitly marks Grace absent before adding the second photo.
    marked = env.client.put(
        f"/api/v1/attendance/sessions/{session_id}/attendance/{grace_pk}",
        json={"status": "absent", "actor": REVIEWER},
    )
    assert marked.status_code == 200, marked.text

    second = env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/images",
        files=[("images", ("second.jpg", b"second", "image/jpeg"))],
    )
    assert second.status_code == 200, second.text
    detail = second.json()
    rows = _by_usn(detail)
    assert detail["photo_count"] == 2
    assert rows["WRK24AT0001"]["status"] == "present"   # from photo 1
    assert rows["WRK24AT0005"]["status"] == "present"   # newly found in photo 2
    assert rows["WRK24AT0002"]["status"] == "absent"    # manual decision kept
    assert rows["WRK24AT0002"]["manually_set"] is True
    assert _confirm(env, session_id).status_code == 200

    closed = env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/images",
        files=[("images", ("late.jpg", b"first", "image/jpeg"))],
    )
    assert closed.status_code == 422
    assert "confirmed" in closed.text


def test_photo_limit_is_enforced_before_processing(env, monkeypatch):
    calls = []

    def process_image(image, **kwargs):
        calls.append(image)
        return [], image

    monkeypatch.setattr(
        CVEngine,
        "from_settings",
        classmethod(lambda cls: SimpleNamespace(
            embedder=SimpleNamespace(model_version="test-sface"), process_image=process_image
        )),
    )
    session_id = _new_session(env)
    too_many = env.client.post(
        f"/api/v1/attendance/sessions/{session_id}/images",
        files=[
            ("images", (f"p{i}.jpg", f"photo-{i}".encode(), "image/jpeg"))
            for i in range(attendance_module.MAX_PHOTOS_PER_SESSION + 1)
        ],
    )
    assert too_many.status_code == 422
    assert calls == []
