"""Deterministic JSON Canonicalization module following RFC 8785 principles."""

from __future__ import annotations

import json
from typing import Any, Dict
from src.pipeline.models import CandidatePost


def to_canonical_dict(candidate: CandidatePost, schema_version: str = "1.0") -> Dict[str, Any]:
    """
    Extract deterministic fields from a CandidatePost into a normalized dictionary.

    CRITICAL DESIGN NOTE:
    The `retrieved_at` timestamp is captured strictly once at collection time
    and treated as immutable stored data. It MUST NEVER be regenerated at
    verification or re-computation time, or verification will fail.
    """
    return {
        "image_sha256": candidate.image_sha256.strip().lower(),
        "retrieved_at": candidate.retrieved_at.strip(),
        "schema_version": str(schema_version).strip(),
        "source": candidate.source.strip(),
        "text": candidate.text.strip(),
        "title": candidate.title.strip(),
        "url": candidate.url.strip(),
    }


def canonicalize_post(candidate: CandidatePost, schema_version: str = "1.0") -> bytes:
    """
    Serialize a CandidatePost into canonical UTF-8 bytes using RFC 8785 rules:
    - Lexicographically sorted keys.
    - Minimal whitespace (separators=(',', ':')).
    - Deterministic UTF-8 encoding.

    Args:
        candidate: CandidatePost instance.
        schema_version: Schema version string.

    Returns:
        Canonical UTF-8 encoded bytes.
    """
    data_dict = to_canonical_dict(candidate, schema_version=schema_version)
    json_str = json.dumps(
        data_dict,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return json_str.encode("utf-8")


def to_canonical_json_string(candidate: CandidatePost, schema_version: str = "1.0") -> str:
    """Return the canonical JSON representation as a string."""
    return canonicalize_post(candidate, schema_version=schema_version).decode("utf-8")
