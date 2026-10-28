import pytest

from classsnap.services.evaluation_service import evaluate_detection, evaluate_matching


def test_detection_evaluation_calculates_metrics_and_zero_edges():
    summary = evaluate_detection(8, 2, 2, latency_ms=12.5)
    assert summary.precision == pytest.approx(0.8)
    assert summary.recall == pytest.approx(0.8)
    assert summary.f1_score == pytest.approx(0.8)
    assert evaluate_detection(0, 0, 0).f1_score == 0.0

    with pytest.raises(ValueError):
        evaluate_detection(-1, 0, 0)


def test_matching_evaluation_keeps_uncertain_results_out_of_match_rate():
    summary = evaluate_matching(
        ["matched_pending_review", "ambiguous", "unknown", "low_quality", "no_candidate"]
    )
    assert summary.total == 5
    assert summary.matched == 1
    assert summary.uncertain == 2
    assert summary.match_rate == pytest.approx(0.2)
