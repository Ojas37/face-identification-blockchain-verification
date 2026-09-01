"""Data models and structures for the verification pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class SearchResult:
    """Represents an initial raw result returned by a search provider."""
    url: str
    title: str
    source: str
    image_url: Optional[str] = None
    text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidatePost:
    """
    Represents a collected candidate post with immutable metadata and local image cache.
    All fields captured at collection time are treated as immutable for hashing and verification.
    """
    id: str
    source: str
    url: str
    title: str
    text: str
    image_url: str
    image_sha256: str
    retrieved_at: str  # ISO-8601 UTC timestamp captured ONCE at collection time
    local_image_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchResult:
    """Represents the outcome of facial comparison between input and a candidate."""
    candidate: CandidatePost
    similarity_score: float
    is_match: bool
    threshold: float
    details: str = ""


@dataclass
class VerificationRecord:
    """Represents the verified record structure stored on the blockchain."""
    content_hash: str  # 64-character SHA-256 hex string
    source: str
    url: str
    timestamp: int  # Unix timestamp on-chain
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    recorder: Optional[str] = None
