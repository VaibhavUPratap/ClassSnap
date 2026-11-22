"""Class/section support and multi-scale enrollment detection."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from classsnap.cv.types import BoundingBox, DetectionResult, FaceQuality
from classsnap.exceptions import ValidationError
from classsnap.schemas.student import StudentCreate
from classsnap.services.attendance_service import AttendanceService
from classsnap.services.enrollment_service import EnrollmentService
from classsnap.services.roster_service import RosterService


def _det(x, y, w, h, conf=0.9):
    quality = FaceQuality(overall_score=0.9, sharpness=100, min_dimension=min(w, h), is_usable=True)
    landmarks = [(x + w * 0.3, y + h * 0.4), (x + w * 0.7, y + h * 0.4), (x + w * 0.5, y + h * 0.6),
                 (x + w * 0.35, y + h * 0.8), (x + w * 0.65, y + h * 0.8)]
    return DetectionResult(bbox=BoundingBox(x, y, w, h), confidence=conf, landmarks=landmarks, quality=quality)


def test_large_photo_retries_downscaled_and_maps_face_back(db_session):
    """At full resolution YuNet fires on clothing; the downscaled pass finds the one face."""
    student = RosterService.create_student(
        db_session, StudentCreate(student_id="SCL24CS0001", first_name="Big", last_name="Photo", has_consent=True)
    )
    full = np.zeros((4000, 3000, 3), dtype=np.uint8)

    def detect(image, score_threshold=None):
        if max(image.shape[:2]) == 4000:  # full resolution: three false boxes
            return [_det(100, 3000, 120, 120), _det(900, 3100, 110, 110), _det(2000, 2900, 130, 130)]
        if max(image.shape[:2]) == 1280:  # downscaled: one real face
            return [_det(320, 200, 400, 480)]
        return []

    engine = MagicMock()
    engine.load_image.return_value = full
    engine.detector.detect.side_effect = detect
    engine.quality_assessor.assess_quality.side_effect = lambda img, det: det.quality
    engine.aligner.align.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
    engine.embedder.extract_embedding.return_value = np.random.rand(128).astype(np.float32)
    engine.embedder.model_name, engine.embedder.model_version = "SFace", "2021dec"

    EnrollmentService(cv_engine=engine).enroll_student_face(db_session, student.id, b"img")

    aligned_on, used = engine.aligner.align.call_args.args
    assert aligned_on is full  # quality/alignment still run on the full-resolution image
    scale = 4000 / 1280
    assert used.bbox.x == round(320 * scale) and used.bbox.w == round(400 * scale)
    assert used.landmarks[0][0] == pytest.approx((320 + 400 * 0.3) * scale)


def test_small_photo_keeps_single_full_resolution_pass(db_session):
    student = RosterService.create_student(
        db_session, StudentCreate(student_id="SCL24CS0002", first_name="Small", last_name="Photo", has_consent=True)
    )
    engine = MagicMock()
    engine.load_image.return_value = np.zeros((800, 600, 3), dtype=np.uint8)
    engine.detector.detect.return_value = [_det(100, 100, 300, 300)]
    engine.quality_assessor.assess_quality.side_effect = lambda img, det: det.quality
    engine.aligner.align.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
    engine.embedder.extract_embedding.return_value = np.random.rand(128).astype(np.float32)
    engine.embedder.model_name, engine.embedder.model_version = "SFace", "2021dec"

    EnrollmentService(cv_engine=engine).enroll_student_face(db_session, student.id, b"img")
    assert engine.detector.detect.call_count == 1
    assert engine.aligner.align.call_args.args[1].bbox.w == 300


def test_class_section_is_normalized_and_filterable(client):
    created = client.post(
        "/api/v1/students",
        json={"student_id": "CLS24CS0001", "first_name": "Asha", "last_name": "K", "class_section": " b "},
    )
    assert created.status_code == 201
    assert created.json()["class_section"] == "B"
    client.post("/api/v1/students", json={"student_id": "CLS24CS0002", "first_name": "Ravi", "last_name": "S", "class_section": "a"})

    only_b = client.get("/api/v1/students", params={"class_section": "b"}).json()
    assert [s["student_id"] for s in only_b] == ["CLS24CS0001"]
    assert client.get("/api/v1/students/classes").json() == ["A", "B"]

    bad = client.post("/api/v1/students", json={"student_id": "CLS24CS0003", "first_name": "X", "last_name": "Y", "class_section": "A B!"})
    assert bad.status_code == 422

    moved = client.patch(f"/api/v1/students/{created.json()['id']}", json={"class_section": "C"})
    assert moved.json()["class_section"] == "C"


def test_session_roster_is_limited_to_its_class(db_session):
    a1 = RosterService.create_student(db_session, StudentCreate(student_id="SEC24CS0001", first_name="A", last_name="One", class_section="A"))
    a2 = RosterService.create_student(db_session, StudentCreate(student_id="SEC24CS0002", first_name="A", last_name="Two", class_section="A"))
    b1 = RosterService.create_student(db_session, StudentCreate(student_id="SEC24CS0003", first_name="B", last_name="One", class_section="B"))

    session = AttendanceService.create_session(db_session, "Physics", class_section="A")
    AttendanceService.begin_processing(db_session, session.id)
    AttendanceService.add_proposals(
        db_session,
        session.id,
        [("f1", "matched_pending_review", a1.id, 0.9, None), ("f2", "unknown", None, 0.2, None)],
    )
    rows = {row.student_id: row.status for row in session.proposed_attendance}
    assert rows == {a1.id: "present", a2.id: "not_detected"}

    # A student from another class cannot be assigned or marked in this session.
    with pytest.raises(ValidationError, match="not in class A"):
        AttendanceService.review_detection(db_session, session.id, "f2", b1.id, True)
    with pytest.raises(Exception):
        AttendanceService.set_student_attendance(db_session, session.id, b1.id, "present")

    confirmed = AttendanceService.confirm(db_session, session.id, actor="teacher")
    assert {r.student_id for r in confirmed.attendance} == {a1.id, a2.id}
