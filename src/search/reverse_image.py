"""Primary Reverse Image Search provider using SerpApi Google Lens engine."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import requests

from src.config import settings
from src.pipeline.models import SearchResult
from src.search.base import SearchError, SearchProvider
from src.utils.logger import logger


class SerpApiLensSearchProvider(SearchProvider):
    """
    Reverse image search provider utilizing Google Lens through SerpApi.
    Directly uploads the face image to discover live web and social media sources.
    """

    SERPAPI_ENDPOINT = "https://serpapi.com/search.json"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.serpapi_api_key

    def search_by_image(self, image_path: Path, max_results: int = 10) -> List[SearchResult]:
        """
        Perform reverse image search by uploading the image to Google Lens via SerpApi.
        """
        if not self.api_key or self.api_key.startswith("your_"):
            raise SearchError(
                "SERPAPI_API_KEY is not configured in .env. "
                "Please set a valid SerpApi API key for reverse image search, "
                "or switch SEARCH_PROVIDER to 'duckduckgo' for keyword-assisted search."
            )

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Input image not found: {path}")

        logger.info(f"[SEARCH] Uploading image to SerpApi Google Lens: {path.name}")

        try:
            with open(path, "rb") as img_file:
                params = {
                    "engine": "google_lens",
                    "api_key": self.api_key,
                    "hl": "en",
                }
                files = {"file": img_file}
                response = requests.post(
                    self.SERPAPI_ENDPOINT,
                    params=params,
                    files=files,
                    timeout=30,
                )

            if response.status_code == 401 or response.status_code == 403:
                raise SearchError(f"SerpApi authentication failed: {response.text}")

            if response.status_code != 200:
                raise SearchError(
                    f"SerpApi returned error status {response.status_code}: {response.text}"
                )

            data = response.json()
        except requests.RequestException as e:
            raise SearchError(f"Network error while querying SerpApi Google Lens: {e}") from e

        results: List[SearchResult] = []
        visual_matches = data.get("visual_matches", [])

        for item in visual_matches[:max_results]:
            url = item.get("link")
            title = item.get("title", "Visual Match")
            source = item.get("source", "Web Source")
            thumbnail = item.get("thumbnail")
            original_image = item.get("original_image", thumbnail)

            if url and (thumbnail or original_image):
                results.append(
                    SearchResult(
                        url=url,
                        title=title,
                        source=source,
                        image_url=original_image or thumbnail,
                        text=item.get("snippet", title),
                        metadata={"serpapi_match_type": "visual_match", "position": item.get("position")},
                    )
                )

        logger.info(f"[SEARCH] Discovered {len(results)} candidate results via Google Lens.")
        return results

    def search_by_query(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Query-assisted search via SerpApi."""
        if not self.api_key or self.api_key.startswith("your_"):
            raise SearchError("SERPAPI_API_KEY is not configured in .env.")

        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": max_results,
            }
            response = requests.get(self.SERPAPI_ENDPOINT, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise SearchError(f"SerpApi query search failed: {e}") from e

        results: List[SearchResult] = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append(
                SearchResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    source=item.get("displayed_link", "Google Search"),
                    text=item.get("snippet", ""),
                    metadata={"position": item.get("position")},
                )
            )
        return results
