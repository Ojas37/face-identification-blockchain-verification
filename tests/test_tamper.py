"""Unit tests for Tamper Detection and Verification Logic (Phase 13)."""

from src.hashing.hasher import compute_content_hash
from src.pipeline.models import CandidatePost


def test_tamper_detection_on_field_mutations():
    """Test that mutating any post field is caught by verification."""
    original_post = CandidatePost(
        id="cand_1",
        source="example.com",
        url="https://example.com/post/1",
        title="Original Title",
        text="Original Content",
        image_url="https://example.com/img.jpg",
        image_sha256="abc123def456",
        retrieved_at="2026-09-01T12:00:00Z",
    )

    original_hash = compute_content_hash(original_post)

    # Mutation 1: Change text
    tampered_text = CandidatePost(
        id="cand_1",
        source="example.com",
        url="https://example.com/post/1",
        title="Original Title",
        text="Tampered Content",
        image_url="https://example.com/img.jpg",
        image_sha256="abc123def456",
        retrieved_at="2026-09-01T12:00:00Z",
    )
    assert compute_content_hash(tampered_text) != original_hash

    # Mutation 2: Change URL
    tampered_url = CandidatePost(
        id="cand_1",
        source="example.com",
        url="https://example.com/post/tampered_url",
        title="Original Title",
        text="Original Content",
        image_url="https://example.com/img.jpg",
        image_sha256="abc123def456",
        retrieved_at="2026-09-01T12:00:00Z",
    )
    assert compute_content_hash(tampered_url) != original_hash

    # Mutation 3: Change Image SHA-256
    tampered_image = CandidatePost(
        id="cand_1",
        source="example.com",
        url="https://example.com/post/1",
        title="Original Title",
        text="Original Content",
        image_url="https://example.com/img.jpg",
        image_sha256="modified_image_hash_789",
        retrieved_at="2026-09-01T12:00:00Z",
    )
    assert compute_content_hash(tampered_image) != original_hash
