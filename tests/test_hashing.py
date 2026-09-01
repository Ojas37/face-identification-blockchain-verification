"""Unit tests for Canonicalization and Cryptographic SHA-256 Hashing (Phases 7 & 8)."""

from src.hashing.canonicalizer import canonicalize_post, to_canonical_dict, to_canonical_json_string
from src.hashing.hasher import compute_content_hash, verify_content_hash
from src.pipeline.models import CandidatePost


def test_canonicalization_determinism():
    """Test that canonical JSON bytes are 100% deterministic across multiple runs."""
    cand = CandidatePost(
        id="cand_123",
        source="twitter.com",
        url="https://twitter.com/example/status/12345",
        title="Breaking News Post",
        text="Sample post body with Unicode characters: ⚡ Face Verification",
        image_url="https://twitter.com/pic.jpg",
        image_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        retrieved_at="2026-09-01T12:00:00+00:00",
    )

    bytes1 = canonicalize_post(cand)
    bytes2 = canonicalize_post(cand)
    assert bytes1 == bytes2

    hash1 = compute_content_hash(cand)
    hash2 = compute_content_hash(cand)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_canonical_key_sorting():
    """Test that keys are sorted lexicographically."""
    cand = CandidatePost(
        id="cand_1",
        source="news.com",
        url="https://news.com/item",
        title="Title",
        text="Text",
        image_url="https://news.com/img.jpg",
        image_sha256="abc",
        retrieved_at="2026-09-01T12:00:00Z",
    )

    json_str = to_canonical_json_string(cand)
    # Expected key order: image_sha256, retrieved_at, schema_version, source, text, title, url
    expected_start = '{"image_sha256":"abc","retrieved_at":"2026-09-01T12:00:00Z","schema_version":"1.0"'
    assert json_str.startswith(expected_start)


def test_hash_sensitivity_to_data_changes():
    """Test that modifying any field changes the resulting SHA-256 fingerprint."""
    original = CandidatePost(
        id="cand_1",
        source="reddit.com",
        url="https://reddit.com/r/test",
        title="Original Title",
        text="Original Text",
        image_url="https://reddit.com/img.png",
        image_sha256="111122223333",
        retrieved_at="2026-09-01T12:00:00Z",
    )

    tampered = CandidatePost(
        id="cand_1",
        source="reddit.com",
        url="https://reddit.com/r/test",
        title="Original Title",
        text="Tampered Text",  # modified field
        image_url="https://reddit.com/img.png",
        image_sha256="111122223333",
        retrieved_at="2026-09-01T12:00:00Z",
    )

    orig_hash = compute_content_hash(original)
    tamp_hash = compute_content_hash(tampered)

    assert orig_hash != tamp_hash
    assert verify_content_hash(original, orig_hash) is True
    assert verify_content_hash(tampered, orig_hash) is False
