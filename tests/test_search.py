"""Unit tests for Web Search Providers and Candidate Collection (Phases 4 & 5)."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.pipeline.models import CandidatePost, SearchResult
from src.search.base import SearchError
from src.search.collector import CandidateCollector
from src.search.duckduckgo import DuckDuckGoSearchProvider
from src.search.reverse_image import SerpApiLensSearchProvider


def test_serpapi_missing_key_error(tmp_path):
    """Test SerpApiLensSearchProvider raises clear error when API key is missing."""
    test_img = tmp_path / "test.jpg"
    test_img.write_bytes(b"dummy")

    provider = SerpApiLensSearchProvider(api_key="")
    with pytest.raises(SearchError) as exc_info:
        provider.search_by_image(test_img)
    assert "SERPAPI_API_KEY is not configured" in str(exc_info.value)


def test_serpapi_lens_mocked_search(tmp_path):
    """Test SerpApiLensSearchProvider parsing of visual matches."""
    test_img = tmp_path / "test.jpg"
    test_img.write_bytes(b"dummy image bytes")

    mock_upload_resp = MagicMock()
    mock_upload_resp.status_code = 200
    mock_upload_resp.json.return_value = {
        "success": True,
        "files": [{"url": "https://d.uguu.se/test.jpg"}]
    }

    mock_serpapi_resp = MagicMock()
    mock_serpapi_resp.status_code = 200
    mock_serpapi_resp.json.return_value = {
        "visual_matches": [
            {
                "link": "https://example.com/post/1",
                "title": "Example Profile",
                "source": "example.com",
                "thumbnail": "https://example.com/thumb1.jpg",
                "snippet": "Verified person profile",
                "position": 1,
            }
        ]
    }

    with patch("requests.post", return_value=mock_upload_resp), \
         patch("requests.get", return_value=mock_serpapi_resp):
        provider = SerpApiLensSearchProvider(api_key="valid_key")
        results = provider.search_by_image(test_img, max_results=5)
        assert len(results) == 1
        assert results[0].url == "https://example.com/post/1"
        assert results[0].title == "Example Profile"
        assert results[0].image_url == "https://example.com/thumb1.jpg"


def test_candidate_collector_deduplication_and_provenance(tmp_path):
    """Test CandidateCollector deduplicates items and captures immutable retrieved_at."""
    collector = CandidateCollector(cache_dir=tmp_path / "cand_cache")

    search_results = [
        SearchResult(
            url="https://example.com/post/1",
            title="Post 1",
            source="example.com",
            image_url=None,
            text="First post text",
        ),
        SearchResult(
            url="https://example.com/post/1",  # Duplicate URL
            title="Post 1 Duplicate",
            source="example.com",
            image_url=None,
            text="First post text duplicate",
        ),
        SearchResult(
            url="https://example.com/post/2",
            title="Post 2",
            source="example.com",
            image_url=None,
            text="Second post text",
        ),
    ]

    with patch.object(collector, "_extract_page_metadata", return_value={}):
        candidates = collector.collect(search_results)

    # Should deduplicate 3 items into 2 unique candidates
    assert len(candidates) == 2
    assert candidates[0].url == "https://example.com/post/1"
    assert candidates[1].url == "https://example.com/post/2"
    assert candidates[0].retrieved_at is not None
    assert "T" in candidates[0].retrieved_at  # ISO format check
