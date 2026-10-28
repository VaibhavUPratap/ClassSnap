"""
Unit and integration tests for BiometricEnrollmentService.
Covers consent checks, single-face validation, embedding storage,
aggregated reference vectors, version mismatch, and deletion flows.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from classsnap.cv.types import BoundingBox, DetectionResult, FaceQuality
from classsnap.exceptions import BiometricProcessingError, ResourceNotFoundError, ValidationError
from classsnap.models.face_template import FaceTemplate
from classsnap.models.student import Student
from classsnap.schemas.student import StudentCreate
from classsnap.services.enrollment_service import EnrollmentService
from classsnap.services.roster_service import RosterService

ASSETS = Path(__file__).resolve().parent / "assets"
SAMPLE_FACE = ASSETS / "sample_face.jpg"
SFACE_PATH = Path("models/face_recognition_sface_2021dec.onnx")


def _make_good_detection(bbox=None):
    bb = bbox or BoundingBox(x=50, y=50, w=100, h=100)
    quality = FaceQuality(
        overall_score=0.85, sharpness=120.0, brightness=130.0,
        contrast=40.0, min_dimension=100, is_usable=True, rejection_reason=None,
    )
    landmarks = [(70., 70.), (110., 70.), (90., 90.), (75., 115.), (105., 115.)]
    return DetectionResult(bbox=bb, confidence=0.91, landmarks=landmarks, quality=quality)


def _make_bad_quality_detection():
    quality = FaceQuality(
        overall_score=0.2, sharpness=2.0, brightness=130.0,
        contrast=5.0, min_dimension=20, is_usable=False,
        rejection_reason="Face resolution too small (20px < 24px)",
    )
    return DetectionResult(
        bbox=BoundingBox(x=10, y=10, w=20, h=20),
        confidence=0.75,
        quality=quality,
    )


def _make_mock_cv_engine(detections):
    """Builds a minimal mock CVEngine with configurable detection results."""
    mock_engine = MagicMock()
    mock_engine.detector.detect.return_value = detections
    mock_engine.quality_assessor.assess_quality.side_effect = lambda img, det: det.quality
    mock_engine.aligner.align.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
    mock_engine.embedder.extract_embedding.return_value = np.random.rand(128).astype(np.float32)
    mock_engine.embedder.model_name = "SFace"
    mock_engine.embedder.model_version = "2021dec"
    mock_engine.load_image.return_value = np.zeros((300, 300, 3), dtype=np.uint8)
    return mock_engine


def _create_consented_student(db, sid="ENRL01"):
    return RosterService.create_student(
        db,
        StudentCreate(student_id=sid, first_name="Test", last_name="Enrollee", has_consent=True),
    )


# ───────────────────────── Consent enforcement ─────────────────────────

def test_enrollment_without_consent_is_rejected(db_session):
    student = RosterService.create_student(
        db_session,
        StudentCreate(student_id="NOCONSENT1", first_name="No", last_name="Consent", has_consent=False),
    )
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([_make_good_detection()]))
    with pytest.raises(ValidationError) as exc:
        svc.enroll_student_face(db_session, student.student_id, b"fake_image_bytes")
    assert "consent" in str(exc.value).lower()


def test_enrollment_grants_consent_inline(db_session):
    """Consent can be granted at enrollment time if not previously set."""
    student = RosterService.create_student(
        db_session,
        StudentCreate(student_id="INLINE1", first_name="Inline", last_name="Consent", has_consent=False),
    )
    good_det = _make_good_detection()
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([good_det]))
    template = svc.enroll_student_face(
        db_session,
        student.student_id,
        b"fake_bytes",
        consent_granted=True,
        consent_notes="Verbal consent given",
    )
    assert template is not None
    db_session.refresh(student)
    assert student.has_consent is True


# ───────────────────────── Face count validation ─────────────────────────

def test_enrollment_fails_with_no_face_detected(db_session):
    student = _create_consented_student(db_session, "NOFACE1")
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([]))
    with pytest.raises(BiometricProcessingError) as exc:
        svc.enroll_student_face(db_session, student.student_id, b"fake")
    assert "no face" in str(exc.value).lower()


def test_enrollment_fails_with_multiple_faces(db_session):
    student = _create_consented_student(db_session, "MULTIFACE1")
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([
        _make_good_detection(BoundingBox(x=10, y=10, w=80, h=80)),
        _make_good_detection(BoundingBox(x=200, y=10, w=80, h=80)),
    ]))
    with pytest.raises(BiometricProcessingError) as exc:
        svc.enroll_student_face(db_session, student.student_id, b"fake")
    assert "multiple faces" in str(exc.value).lower()


# ───────────────────────── Quality rejection ─────────────────────────

def test_enrollment_fails_on_low_quality_face(db_session):
    student = _create_consented_student(db_session, "LOWQ1")
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([_make_bad_quality_detection()]))
    with pytest.raises(BiometricProcessingError) as exc:
        svc.enroll_student_face(db_session, student.student_id, b"fake")
    assert "quality" in str(exc.value).lower()


# ───────────────────────── Successful enrollment ─────────────────────────

def test_successful_enrollment_stores_normalized_embedding(db_session):
    student = _create_consented_student(db_session, "SUCC1")
    fixed_emb = np.ones(128, dtype=np.float32)
    fixed_emb /= np.linalg.norm(fixed_emb)

    mock_engine = _make_mock_cv_engine([_make_good_detection()])
    mock_engine.embedder.extract_embedding.return_value = fixed_emb

    svc = EnrollmentService(cv_engine=mock_engine)
    template = svc.enroll_student_face(db_session, student.student_id, b"fake")

    assert template.id is not None
    assert template.model_name == "SFace"
    assert template.model_version == "2021dec"
    assert template.embedding_dim == 128
    assert template.quality_score > 0.0

    stored_vec = template.get_embedding_vector()
    assert stored_vec.shape == (128,)
    assert pytest.approx(np.linalg.norm(stored_vec), abs=1e-5) == 1.0


# ───────────────────────── Multiple references ─────────────────────────

def test_multiple_templates_per_student(db_session):
    student = _create_consented_student(db_session, "MULTI1")
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([_make_good_detection()]))

    t1 = svc.enroll_student_face(db_session, student.student_id, b"img1")
    t2 = svc.enroll_student_face(db_session, student.student_id, b"img2", is_primary=False)

    db_session.refresh(student)
    assert len(student.templates) == 2


def test_aggregated_embedding_is_unit_normalized(db_session):
    student = _create_consented_student(db_session, "AGG1")
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([_make_good_detection()]))
    svc.enroll_student_face(db_session, student.student_id, b"img1")
    svc.enroll_student_face(db_session, student.student_id, b"img2")

    agg = EnrollmentService.get_aggregated_student_embedding(
        db_session, student.student_id, required_model_version="2021dec"
    )
    assert agg is not None
    assert agg.shape == (128,)
    assert pytest.approx(np.linalg.norm(agg), abs=1e-5) == 1.0


# ───────────────────────── Version mismatch ─────────────────────────

def test_version_filtered_aggregation_returns_none_for_wrong_version(db_session):
    student = _create_consented_student(db_session, "VER1")
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([_make_good_detection()]))
    svc.enroll_student_face(db_session, student.student_id, b"img1")

    # Filter by an incompatible version string
    result = EnrollmentService.get_aggregated_student_embedding(
        db_session, student.student_id, required_model_version="arcface_v3"
    )
    assert result is None


# ───────────────────────── Deletion ─────────────────────────

def test_delete_single_template(db_session):
    student = _create_consented_student(db_session, "DEL_T1")
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([_make_good_detection()]))
    template = svc.enroll_student_face(db_session, student.student_id, b"img1")
    tid = template.id

    deleted = EnrollmentService.delete_template(db_session, tid)
    assert deleted is True

    db_session.refresh(student)
    assert len(student.templates) == 0


def test_delete_all_student_templates(db_session):
    student = _create_consented_student(db_session, "DEL_ALL1")
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([_make_good_detection()]))
    svc.enroll_student_face(db_session, student.student_id, b"img1")
    svc.enroll_student_face(db_session, student.student_id, b"img2")

    count = EnrollmentService.delete_all_student_templates(db_session, student.student_id)
    assert count == 2

    db_session.refresh(student)
    assert len(student.templates) == 0


# ───────────────────────── Non-existent student ─────────────────────────

def test_enrollment_for_nonexistent_student_raises(db_session):
    svc = EnrollmentService(cv_engine=_make_mock_cv_engine([_make_good_detection()]))
    with pytest.raises(ResourceNotFoundError):
        svc.enroll_student_face(db_session, "GHOST_ID_XYZ", b"fake")


@pytest.mark.skipif(not SAMPLE_FACE.exists(), reason="Sample face asset not present")
@pytest.mark.skipif(not SFACE_PATH.exists(), reason="SFace model not present")
def test_enrollment_end_to_end_with_real_cv_engine(db_session):
    """Integration test: enroll a real student face using actual YuNet + SFace models."""
    from classsnap.cv.engine import CVEngine
    real_engine = CVEngine.from_settings()

    student = _create_consented_student(db_session, "REALCV1")
    svc = EnrollmentService(cv_engine=real_engine)

    with open(SAMPLE_FACE, "rb") as f:
        image_bytes = f.read()

    template = svc.enroll_student_face(db_session, student.student_id, image_bytes)

    assert template.model_name == "SFace"
    assert template.embedding_dim == 128
    vec = template.get_embedding_vector()
    assert pytest.approx(np.linalg.norm(vec), abs=1e-5) == 1.0
    assert template.quality_score > 0.5
