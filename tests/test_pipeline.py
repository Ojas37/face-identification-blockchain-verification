"""End-to-end integration test for full PipelineOrchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import pytest

from src.face.base import DetectedFace, FaceEmbedding
from src.pipeline.models import CandidatePost, SearchResult, VerificationRecord
from src.pipeline.orchestrator import PipelineOrchestrator


@pytest.fixture
def test_image(tmp_path):
    """Create a temporary test image file."""
    img_path = tmp_path / "test_face.png"
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.circle(img, (150, 150), 50, (255, 255, 255), -1)
    cv2.imwrite(str(img_path), img)
    return img_path


def test_full_pipeline_orchestrator_mocked(test_image, tmp_path):
    """Test full execution of all 14 phases with mocked external dependencies."""
    mock_blockchain = MagicMock()
    fake_tx = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    fake_hash = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

    mock_blockchain.upload_record.return_value = VerificationRecord(
        content_hash=fake_hash,
        source="example.com",
        url="https://example.com/post/verified",
        timestamp=1700000000,
        tx_hash=fake_tx,
        block_number=101,
        recorder="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    )

    # Return same hash for verification
    def retrieve_side_effect(content_hash, tx_hash=None):
        return VerificationRecord(
            content_hash=content_hash,
            source="example.com",
            url="https://example.com/post/verified",
            timestamp=1700000000,
            tx_hash=tx_hash,
            block_number=101,
        )
    mock_blockchain.retrieve_record.side_effect = retrieve_side_effect

    orchestrator = PipelineOrchestrator(
        search_provider_name="duckduckgo",
        similarity_threshold=0.363,
        blockchain_client=mock_blockchain,
    )

    # Mock face detection & encoding
    fake_face = DetectedFace(bbox=(50, 50, 100, 100), confidence=0.99)
    fake_emb = FaceEmbedding(vector=np.ones(128, dtype=np.float32) / np.sqrt(128))

    with patch.object(orchestrator.detector, "detect", return_value=[fake_face]), \
         patch.object(orchestrator.encoder, "encode", return_value=fake_emb), \
         patch.object(orchestrator.search_provider, "search_by_image", return_value=[
             SearchResult(url="https://example.com/post/verified", title="Verified Post", source="example.com", image_url=None, text="Verified snippet")
         ]), \
         patch.object(orchestrator.comparator, "compare_candidate") as mock_comp:

        from src.pipeline.models import MatchResult
        cand_post = CandidatePost(
            id="c1",
            source="example.com",
            url="https://example.com/post/verified",
            title="Verified Post",
            text="Verified snippet",
            image_url="",
            image_sha256="abc",
            retrieved_at="2026-09-01T12:00:00Z",
        )
        mock_comp.return_value = MatchResult(
            candidate=cand_post,
            similarity_score=0.92,
            is_match=True,
            threshold=0.363,
            details="Match found",
        )

        # Run pipeline
        results = orchestrator.execute(image_path=test_image, run_tamper_test=True)

        assert results["match_found"] is True
        assert results["verification_status"] == "VERIFIED"
        assert results["tamper_test_status"] == "TAMPER_DETECTED"
        assert results["similarity_score"] == 0.92
