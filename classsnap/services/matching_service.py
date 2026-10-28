"""
Identity Matching Service for ClassSnap.
Compares classroom face embeddings against enrolled student references using
cosine similarity, applies configurable thresholds, handles uncertainty,
prevents duplicate one-to-one assignment via bipartite matching.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from classsnap.logger import get_logger

logger = get_logger("services.matching")

# --- Status constants ---
STATUS_MATCHED = "matched_pending_review"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_LOW_QUALITY = "low_quality"
STATUS_NO_CANDIDATE = "no_candidate"
STATUS_UNKNOWN = "unknown"


@dataclass
class CandidateMatch:
    """A ranked identity candidate for a given face detection."""
    student_id: str
    student_name: str
    similarity: float
    rank: int


@dataclass
class MatchResult:
    """Full match outcome for a single face detection."""
    detection_id: str
    status: str
    top_candidate: Optional[CandidateMatch] = None
    second_candidate: Optional[CandidateMatch] = None
    similarity_gap: float = 0.0
    rejection_reason: Optional[str] = None
    embedding_model_version: Optional[str] = None
    all_candidates: List[CandidateMatch] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "detection_id": self.detection_id,
            "status": self.status,
            "top_candidate": {
                "student_id": self.top_candidate.student_id,
                "student_name": self.top_candidate.student_name,
                "similarity": round(self.top_candidate.similarity, 4),
                "rank": self.top_candidate.rank,
            } if self.top_candidate else None,
            "second_candidate": {
                "student_id": self.second_candidate.student_id,
                "similarity": round(self.second_candidate.similarity, 4),
            } if self.second_candidate else None,
            "similarity_gap": round(self.similarity_gap, 4),
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class MatchingThresholds:
    """Tunable thresholds controlling matching behaviour."""
    accept: float = 0.38      # Cosine similarity above which a match is accepted
    ambiguity_gap: float = 0.06  # Minimum gap between top-2 scores for unambiguous assignment
    low_quality: float = 0.0  # Placeholder: low-quality faces filtered before matching

    def to_dict(self) -> dict:
        return {
            "accept": self.accept,
            "ambiguity_gap": self.ambiguity_gap,
        }


@dataclass(frozen=True)
class CalibrationSample:
    """A labeled pair of embeddings used to calibrate acceptance thresholds."""

    query: np.ndarray
    reference: np.ndarray
    same_identity: bool


def calibrate_thresholds(
    samples: Sequence[CalibrationSample],
    *,
    target_false_accept_rate: float = 0.01,
    ambiguity_gap: float = 0.06,
) -> MatchingThresholds:
    """Calibrate an acceptance threshold from labeled, consented embedding pairs.

    The threshold is the highest impostor similarity at or below the requested
    false-accept percentile. A genuine-pair score is required above it so that
    calibration cannot silently produce a threshold that rejects every match.
    """
    if not 0 < target_false_accept_rate <= 1:
        raise ValueError("target_false_accept_rate must be in the interval (0, 1]")
    if ambiguity_gap < 0:
        raise ValueError("ambiguity_gap cannot be negative")

    genuine = [
        MatchingService.cosine_similarity(sample.query, sample.reference)
        for sample in samples
        if sample.same_identity
    ]
    impostor = [
        MatchingService.cosine_similarity(sample.query, sample.reference)
        for sample in samples
        if not sample.same_identity
    ]
    if not genuine or not impostor:
        raise ValueError("Calibration requires both genuine and impostor samples")

    # The rank-based index avoids interpolation differences across NumPy
    # versions and keeps calibration deterministic.
    impostor_sorted = sorted(impostor)
    index = min(
        len(impostor_sorted) - 1,
        int(np.ceil((1.0 - target_false_accept_rate) * len(impostor_sorted))) - 1,
    )
    threshold = impostor_sorted[max(0, index)]
    genuine_floor = min(genuine)
    if threshold >= genuine_floor:
        raise ValueError(
            "Calibration data has no separable genuine/impostor threshold"
        )
    return MatchingThresholds(accept=threshold, ambiguity_gap=ambiguity_gap)


class MatchingService:
    """
    Matches face embeddings against an enrolled roster using cosine similarity.
    Applies threshold logic and bipartite Hungarian matching for 1-to-1 assignment.
    """

    def __init__(self, thresholds: Optional[MatchingThresholds] = None):
        self.thresholds = thresholds or MatchingThresholds()

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        """Cosine similarity between two unit-norm vectors (efficient dot product)."""
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-8 or n2 < 1e-8:
            return 0.0
        return float(np.dot(v1, v2) / (n1 * n2))

    def match_single(
        self,
        detection_id: str,
        face_embedding: np.ndarray,
        roster_embeddings: Dict[str, Union[Tuple[str, np.ndarray], Tuple[str, np.ndarray, str]]],
        model_version: Optional[str] = None,
    ) -> MatchResult:
        """
        Matches one face embedding against all enrolled student references.

        Args:
            detection_id: Unique ID of the face detection.
            face_embedding: 128D unit-normalized float32 vector.
            roster_embeddings: dict of {student_id: (student_name, embedding_vector)}.
            model_version: Locks comparison to a specific model version.

        Returns:
            MatchResult with status, candidate(s), and similarity gap.
        """
        compatible = self._compatible_roster(roster_embeddings, model_version)
        if not compatible:
            return MatchResult(
                detection_id=detection_id,
                status=STATUS_NO_CANDIDATE,
                rejection_reason=(
                    "Roster has no enrolled face templates"
                    if not roster_embeddings
                    else f"No enrolled face templates match model version '{model_version}'"
                ),
                embedding_model_version=model_version,
            )

        # Compute cosine similarity against all enrolled references
        scored: List[Tuple[float, str, str]] = []  # (similarity, student_id, name)
        for sid, (name, ref_vec) in compatible.items():
            if np.asarray(ref_vec).size != np.asarray(face_embedding).size:
                continue
            sim = self.cosine_similarity(face_embedding, ref_vec)
            scored.append((sim, sid, name))

        if not scored:
            return MatchResult(
                detection_id=detection_id,
                status=STATUS_NO_CANDIDATE,
                rejection_reason="No enrolled template has the same embedding dimension",
                embedding_model_version=model_version,
            )

        scored.sort(key=lambda x: x[0], reverse=True)
        top_sim, top_sid, top_name = scored[0]

        top_candidate = CandidateMatch(
            student_id=top_sid,
            student_name=top_name,
            similarity=top_sim,
            rank=1,
        )
        all_candidates = [
            CandidateMatch(student_id=s, student_name=n, similarity=sim, rank=i + 1)
            for i, (sim, s, n) in enumerate(scored)
        ]

        second_candidate: Optional[CandidateMatch] = None
        gap = 0.0
        if len(scored) >= 2:
            second_sim, second_sid, second_name = scored[1]
            second_candidate = CandidateMatch(
                student_id=second_sid, student_name=second_name, similarity=second_sim, rank=2
            )
            gap = top_sim - second_sim

        # --- Threshold decision logic ---
        if top_sim < self.thresholds.accept:
            return MatchResult(
                detection_id=detection_id,
                status=STATUS_UNKNOWN,
                top_candidate=top_candidate,
                second_candidate=second_candidate,
                similarity_gap=gap,
                rejection_reason=f"Best similarity {top_sim:.4f} < acceptance threshold {self.thresholds.accept}",
                embedding_model_version=model_version,
                all_candidates=all_candidates,
            )

        if len(scored) >= 2 and gap < self.thresholds.ambiguity_gap:
            return MatchResult(
                detection_id=detection_id,
                status=STATUS_AMBIGUOUS,
                top_candidate=top_candidate,
                second_candidate=second_candidate,
                similarity_gap=gap,
                rejection_reason=f"Similarity gap {gap:.4f} < ambiguity threshold {self.thresholds.ambiguity_gap}",
                embedding_model_version=model_version,
                all_candidates=all_candidates,
            )

        return MatchResult(
            detection_id=detection_id,
            status=STATUS_MATCHED,
            top_candidate=top_candidate,
            second_candidate=second_candidate,
            similarity_gap=gap,
            embedding_model_version=model_version,
            all_candidates=all_candidates,
        )

    @staticmethod
    def _compatible_roster(
        roster_embeddings: Dict[str, Union[Tuple[str, np.ndarray], Tuple[str, np.ndarray, str]]],
        model_version: Optional[str],
    ) -> Dict[str, Tuple[str, np.ndarray]]:
        """Normalize roster entries and remove incompatible model versions."""
        compatible: Dict[str, Tuple[str, np.ndarray]] = {}
        for student_id, entry in roster_embeddings.items():
            if len(entry) == 2:
                name, vector = entry
                entry_version = None
            else:
                name, vector, entry_version = entry
            if model_version is not None and entry_version not in (None, model_version):
                continue
            compatible[student_id] = (name, np.asarray(vector, dtype=np.float32))
        return compatible

    def match_all(
        self,
        detections: List[Tuple[str, Optional[np.ndarray], str]],
        roster_embeddings: Dict[str, Union[Tuple[str, np.ndarray], Tuple[str, np.ndarray, str]]],
        model_version: Optional[str] = None,
    ) -> List[MatchResult]:
        """
        Matches a list of face detections against the roster using greedy bipartite matching.
        Enforces one-to-one assignment: each student can only be matched to ONE detection.

        Args:
            detections: List of (detection_id, embedding_or_None, quality_status).
            roster_embeddings: dict of {student_id: (student_name, embedding_vector)}.
            model_version: Model version string for audit.

        Returns:
            List of MatchResult in detection order, with bipartite conflicts resolved.
        """
        # Step 1: Compute raw match results for all usable detections
        raw_results: List[MatchResult] = []
        for det_id, embedding, quality_status in detections:
            if quality_status == "low_quality" or embedding is None:
                raw_results.append(MatchResult(
                    detection_id=det_id,
                    status=STATUS_LOW_QUALITY,
                    rejection_reason="Face was flagged as low quality or embedding unavailable",
                    embedding_model_version=model_version,
                ))
                continue
            emb_arr = np.array(embedding, dtype=np.float32)
            result = self.match_single(det_id, emb_arr, roster_embeddings, model_version)
            raw_results.append(result)

        # Step 2: Bipartite 1-to-1 conflict resolution
        return self._resolve_conflicts(raw_results)

    def _resolve_conflicts(self, results: List[MatchResult]) -> List[MatchResult]:
        """
        Ensures no student is claimed by more than one detection.
        Among competing detections for the same student, the highest-similarity
        match wins; others are downgraded to STATUS_UNKNOWN.
        """
        eligible = [r for r in results if r.status == STATUS_MATCHED and r.all_candidates]
        assignments: Dict[str, str] = {}
        # Process detections by strongest available candidate first. Since each
        # result is already deterministically ranked, this is stable across runs.
        for result in sorted(
            eligible,
            key=lambda r: (
                -r.top_candidate.similarity if r.top_candidate else 0.0,
                r.detection_id,
            ),
        ):
            for candidate in result.all_candidates:
                if candidate.similarity < self.thresholds.accept:
                    break
                if candidate.student_id not in assignments:
                    assignments[candidate.student_id] = result.detection_id
                    break

        assigned_detection_ids = set(assignments.values())
        final: List[MatchResult] = []
        for r in results:
            if r.status == STATUS_MATCHED and r.detection_id not in assigned_detection_ids:
                final.append(MatchResult(
                    detection_id=r.detection_id,
                    status=STATUS_UNKNOWN,
                    top_candidate=r.top_candidate,
                    second_candidate=r.second_candidate,
                    similarity_gap=r.similarity_gap,
                    rejection_reason="No unique student assignment remained after duplicate resolution",
                    embedding_model_version=r.embedding_model_version,
                    all_candidates=r.all_candidates,
                ))
            else:
                final.append(r)

        return final
