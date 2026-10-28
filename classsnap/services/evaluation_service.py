"""Deterministic evaluation summaries for CV and identity matching."""

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class DetectionEvaluation:
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float
    recall: float
    f1_score: float
    latency_ms: float | None = None


@dataclass(frozen=True)
class MatchingEvaluation:
    total: int
    matched: int
    uncertain: int
    low_quality: int
    no_candidate: int
    match_rate: float


def evaluate_detection(
    true_positive: int,
    false_positive: int,
    false_negative: int,
    latency_ms: float | None = None,
) -> DetectionEvaluation:
    """Calculate safe precision, recall, and F1 metrics from benchmark counts."""
    for value in (true_positive, false_positive, false_negative):
        if value < 0:
            raise ValueError("Evaluation counts cannot be negative")
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = true_positive / precision_denominator if precision_denominator else 0.0
    recall = true_positive / recall_denominator if recall_denominator else 0.0
    f1_score = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return DetectionEvaluation(
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        latency_ms=latency_ms,
    )


def evaluate_matching(statuses: Iterable[str]) -> MatchingEvaluation:
    """Summarize match outcomes while keeping uncertain results unassigned."""
    counts: Mapping[str, int] = {}
    for status in statuses:
        counts[status] = counts.get(status, 0) + 1
    total = sum(counts.values())
    matched = counts.get("matched_pending_review", 0)
    uncertain = sum(counts.get(status, 0) for status in ("unknown", "ambiguous"))
    low_quality = counts.get("low_quality", 0)
    no_candidate = counts.get("no_candidate", 0)
    return MatchingEvaluation(
        total=total,
        matched=matched,
        uncertain=uncertain,
        low_quality=low_quality,
        no_candidate=no_candidate,
        match_rate=matched / total if total else 0.0,
    )
