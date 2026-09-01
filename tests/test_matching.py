"""Unit tests for Face Matching and Candidate Ranking (Phase 6)."""

from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
import pytest

from src.face.base import FaceEmbedding, DetectedFace
from src.matching.comparator import FaceComparator
from src.matching.ranker import CandidateRanker
from src.pipeline.models import CandidatePost


@pytest.fixture
def mock_embedding():
    """Create a normalized 128D unit vector."""
    vec = np.zeros(128, dtype=np.float32)
    vec[0] = 1.0
    return FaceEmbedding(vector=vec)


@pytest.fixture
def mock_candidate(tmp_path):
    """Create a dummy candidate post with an existing image file."""
    img_path = tmp_path / "cand.jpg"
    img_path.write_bytes(b"dummy")
    return CandidatePost(
        id="cand_1",
        source="example.com",
        url="https://example.com/post/1",
        title="Candidate 1",
        text="Sample post text",
        image_url="https://example.com/cand.jpg",
        image_sha256="abc123",
        retrieved_at="2026-09-01T12:00:00Z",
        local_image_path=img_path,
    )


def test_face_comparator_no_image():
    """Test comparator handles candidates without local images."""
    comparator = FaceComparator(threshold=0.363)
    cand_no_img = CandidatePost(
        id="cand_no_img",
        source="example.com",
        url="https://example.com/post/no_img",
        title="No Img",
        text="No Img",
        image_url="",
        image_sha256="",
        retrieved_at="2026-09-01T12:00:00Z",
        local_image_path=None,
    )
    vec = np.zeros(128, dtype=np.float32)
    vec[0] = 1.0
    res = comparator.compare_candidate(FaceEmbedding(vector=vec), cand_no_img)
    assert not res.is_match
    assert res.similarity_score == 0.0


def test_candidate_ranker_ordering(mock_embedding):
    """Test CandidateRanker correctly orders candidates by similarity score and filters by threshold."""
    mock_comparator = MagicMock()

    cand1 = CandidatePost(id="1", source="s1", url="https://example.com/1", title="T1", text="", image_url="", image_sha256="", retrieved_at="2026-09-01T12:00:00Z")
    cand2 = CandidatePost(id="2", source="s2", url="https://example.com/2", title="T2", text="", image_url="", image_sha256="", retrieved_at="2026-09-01T12:00:00Z")
    cand3 = CandidatePost(id="3", source="s3", url="https://example.com/3", title="T3", text="", image_url="", image_sha256="", retrieved_at="2026-09-01T12:00:00Z")

    from src.pipeline.models import MatchResult

    # Mock comparison outcomes
    mock_comparator.threshold = 0.363
    mock_comparator.compare_candidate.side_effect = [
        MatchResult(candidate=cand1, similarity_score=0.20, is_match=False, threshold=0.363),
        MatchResult(candidate=cand2, similarity_score=0.85, is_match=True, threshold=0.363),
        MatchResult(candidate=cand3, similarity_score=0.50, is_match=True, threshold=0.363),
    ]

    ranker = CandidateRanker(comparator=mock_comparator)
    best_match, all_ranked = ranker.rank_candidates(mock_embedding, [cand1, cand2, cand3])

    assert best_match is not None
    assert best_match.candidate.id == "2"
    assert best_match.similarity_score == 0.85

    # Check rank order: cand2 (0.85) -> cand3 (0.50) -> cand1 (0.20)
    assert all_ranked[0].candidate.id == "2"
    assert all_ranked[1].candidate.id == "3"
    assert all_ranked[2].candidate.id == "1"


def test_candidate_ranker_no_match(mock_embedding):
    """Test ranker returns None when all candidates score below threshold."""
    mock_comparator = MagicMock()
    mock_comparator.threshold = 0.363

    cand1 = CandidatePost(id="1", source="s1", url="https://example.com/1", title="T1", text="", image_url="", image_sha256="", retrieved_at="2026-09-01T12:00:00Z")

    from src.pipeline.models import MatchResult
    mock_comparator.compare_candidate.return_value = MatchResult(
        candidate=cand1, similarity_score=0.15, is_match=False, threshold=0.363
    )

    ranker = CandidateRanker(comparator=mock_comparator)
    best_match, all_ranked = ranker.rank_candidates(mock_embedding, [cand1])

    assert best_match is None
    assert len(all_ranked) == 1
