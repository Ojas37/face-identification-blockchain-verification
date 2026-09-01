"""Cryptographic SHA-256 content fingerprint hashing module."""

from __future__ import annotations

import hashlib
from typing import Union
from src.hashing.canonicalizer import canonicalize_post
from src.pipeline.models import CandidatePost


def compute_content_hash(data: Union[bytes, str, CandidatePost]) -> str:
    """
    Compute cryptographic SHA-256 fingerprint from canonical data or CandidatePost.

    Args:
        data: CandidatePost, canonical bytes, or JSON string.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest string.
    """
    if isinstance(data, CandidatePost):
        canonical_bytes = canonicalize_post(data)
    elif isinstance(data, str):
        canonical_bytes = data.encode("utf-8")
    elif isinstance(data, (bytes, bytearray)):
        canonical_bytes = bytes(data)
    else:
        raise TypeError(f"Unsupported data type for content hashing: {type(data)}")

    return hashlib.sha256(canonical_bytes).hexdigest().lower()


def verify_content_hash(candidate: CandidatePost, expected_hash: str) -> bool:
    """
    Verify whether the candidate post data matches the expected SHA-256 fingerprint.

    Args:
        candidate: CandidatePost to verify.
        expected_hash: Expected 64-character SHA-256 digest string.

    Returns:
        True if local canonical hash matches expected hash exactly, False otherwise.
    """
    calculated_hash = compute_content_hash(candidate)
    return calculated_hash.strip().lower() == expected_hash.strip().lower()
