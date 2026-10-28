from types import SimpleNamespace

from classsnap.cv.types import BoundingBox, DetectionResult, FaceQuality
from classsnap.cv.engine import CVEngine


def test_classroom_image_processing_creates_review_proposals(client, monkeypatch):
    detection = DetectionResult(
        bbox=BoundingBox(10, 10, 40, 40),
        confidence=0.9,
        quality=FaceQuality(is_usable=True),
        embedding=[1.0, 0.0],
    )
    fake_engine = SimpleNamespace(
        embedder=SimpleNamespace(model_version="test-model"),
        process_image=lambda image, **kwargs: ([detection], image),
    )
    monkeypatch.setattr(
        CVEngine,
        "from_settings",
        classmethod(lambda cls: fake_engine),
    )

    created = client.post(
        "/api/v1/attendance/sessions",
        json={"name": "Processing API Session"},
    )
    session_id = created.json()["id"]
    assert client.post(f"/api/v1/attendance/sessions/{session_id}/process").status_code == 200

    processed = client.post(
        f"/api/v1/attendance/sessions/{session_id}/image",
        files={"image": ("classroom.jpg", b"image-bytes", "image/jpeg")},
    )
    assert processed.status_code == 200
    assert processed.json()["status"] == "review_required"
