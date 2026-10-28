import numpy as np
import pytest

from classsnap.services.matching_service import (
    CalibrationSample,
    MatchingService,
    MatchingThresholds,
    STATUS_AMBIGUOUS,
    STATUS_LOW_QUALITY,
    STATUS_MATCHED,
    STATUS_NO_CANDIDATE,
    STATUS_UNKNOWN,
    calibrate_thresholds,
)


def _vector(*values: float) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def test_known_identity_is_matched_with_ranked_candidates():
    service = MatchingService(MatchingThresholds(accept=0.8, ambiguity_gap=0.05))
    result = service.match_single(
        "face-1",
        _vector(1, 0),
        {
            "student-a": ("Alice", _vector(1, 0)),
            "student-b": ("Bob", _vector(0, 1)),
        },
    )

    assert result.status == STATUS_MATCHED
    assert result.top_candidate.student_id == "student-a"
    assert result.similarity_gap > 0.05
    assert len(result.all_candidates) == 2


def test_unknown_and_ambiguous_edges_are_explicit():
    service = MatchingService(MatchingThresholds(accept=0.8, ambiguity_gap=0.1))
    unknown = service.match_single("unknown", _vector(0, 1), {"a": ("A", _vector(1, 0))})
    ambiguous = service.match_single(
        "ambiguous",
        _vector(1, 0),
        {"a": ("A", _vector(1, 0)), "b": ("B", _vector(1, 0))},
    )

    assert unknown.status == STATUS_UNKNOWN
    assert ambiguous.status == STATUS_AMBIGUOUS
    assert ambiguous.similarity_gap == 0


def test_empty_and_incompatible_rosters_have_no_candidate_status():
    service = MatchingService()
    assert service.match_single("empty", _vector(1, 0), {}) .status == STATUS_NO_CANDIDATE
    result = service.match_single(
        "wrong-version",
        _vector(1, 0),
        {"a": ("A", _vector(1, 0), "old-model")},
        model_version="new-model",
    )
    assert result.status == STATUS_NO_CANDIDATE
    assert "version" in result.rejection_reason


def test_low_quality_is_not_matched():
    result = MatchingService().match_all(
        [("low", None, "low_quality")],
        {"a": ("A", _vector(1, 0))},
    )[0]
    assert result.status == STATUS_LOW_QUALITY


def test_duplicate_identity_is_assigned_once_deterministically():
    service = MatchingService(MatchingThresholds(accept=0.8, ambiguity_gap=0.01))
    results = service.match_all(
        [
            ("weak", _vector(1, 0), "usable"),
            ("strong", _vector(1, 0), "usable"),
        ],
        {"a": ("A", _vector(1, 0))},
    )

    assert [result.status for result in results] == [STATUS_UNKNOWN, STATUS_MATCHED]
    assert "unique student assignment" in results[0].rejection_reason


def test_calibration_requires_separable_labeled_samples():
    samples = [
        CalibrationSample(_vector(1, 0), _vector(1, 0), True),
        CalibrationSample(_vector(0, 1), _vector(0, 1), True),
        CalibrationSample(_vector(1, 0), _vector(0, 1), False),
    ]
    thresholds = calibrate_thresholds(samples, target_false_accept_rate=1.0)
    assert thresholds.accept == pytest.approx(0.0)

    with pytest.raises(ValueError, match="both genuine and impostor"):
        calibrate_thresholds(samples[:2])
