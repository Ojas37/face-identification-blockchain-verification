"""Candidate ranking and match selection module."""

from __future__ import annotations

from typing import List, Optional, Tuple
from src.face.base import FaceEmbedding
from src.matching.comparator import FaceComparator
from src.pipeline.models import CandidatePost, MatchResult
from src.utils.logger import logger


class CandidateRanker:
    """
    Ranks candidates by face similarity score and selects the best matching candidate.
    """

    def __init__(self, comparator: Optional[FaceComparator] = None) -> None:
        self.comparator = comparator or FaceComparator()

    def rank_candidates(
        self,
        input_embedding: FaceEmbedding,
        candidates: List[CandidatePost],
    ) -> Tuple[Optional[MatchResult], List[MatchResult]]:
        """
        Evaluate and rank all candidates against the input face embedding.

        Args:
            input_embedding: 128D FaceEmbedding of target person.
            candidates: List of CandidatePost objects.

        Returns:
            Tuple of (best_match or None, sorted list of all MatchResults).
        """
        if not candidates:
            logger.info("[RANKER] No candidates provided for ranking.")
            return None, []

        results: List[MatchResult] = []
        logger.info(f"[RANKER] Comparing target face against {len(candidates)} candidate(s)...")

        for idx, candidate in enumerate(candidates, 1):
            match_res = self.comparator.compare_candidate(input_embedding, candidate)
            results.append(match_res)
            logger.info(
                f"  Candidate #{idx} ({candidate.source}): similarity = {match_res.similarity_score:.4f} "
                f"-> {'MATCH' if match_res.is_match else 'NO MATCH'}"
            )

        # Sort in descending order of similarity score
        ranked_results = sorted(results, key=lambda r: r.similarity_score, reverse=True)

        # Select the best candidate that satisfies the threshold
        best_match: Optional[MatchResult] = None
        if ranked_results and ranked_results[0].is_match:
            best_match = ranked_results[0]
            logger.info(
                f"[RANKER] ✓ BEST MATCH SELECTED: {best_match.candidate.url} "
                f"(Score: {best_match.similarity_score:.4f} >= {best_match.threshold:.4f})"
            )
        else:
            highest_score = ranked_results[0].similarity_score if ranked_results else 0.0
            logger.info(
                f"[RANKER] ✗ NO MATCH FOUND (Top score: {highest_score:.4f} < {self.comparator.threshold:.4f})"
            )

        return best_match, ranked_results
