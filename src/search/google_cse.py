"""Secondary search provider using Google Custom Search JSON API."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import requests

from src.config import settings
from src.pipeline.models import SearchResult
from src.search.base import SearchError, SearchProvider
from src.utils.logger import logger


class GoogleCSESearchProvider(SearchProvider):
    """
    Google Custom Search JSON API provider.
    Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ENGINE_ID (cx).
    """

    CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        engine_id: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.google_cse_api_key
        self.engine_id = engine_id or settings.google_cse_engine_id

    def search_by_image(self, image_path: Path, max_results: int = 10) -> List[SearchResult]:
        query = Path(image_path).stem.replace("_", " ").replace("-", " ")
        logger.info(f"[SEARCH] Google CSE query derived from image: '{query}'")
        return self.search_by_query(query, max_results=max_results)

    def search_by_query(self, query: str, max_results: int = 10) -> List[SearchResult]:
        if not self.api_key or not self.engine_id:
            raise SearchError(
                "GOOGLE_CSE_API_KEY or GOOGLE_CSE_ENGINE_ID is not configured in .env."
            )

        try:
            params = {
                "key": self.api_key,
                "cx": self.engine_id,
                "q": query,
                "num": min(max_results, 10),
                "searchType": "image",
            }
            response = requests.get(self.CSE_ENDPOINT, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise SearchError(f"Google CSE search failed: {e}") from e

        results: List[SearchResult] = []
        for item in data.get("items", []):
            results.append(
                SearchResult(
                    url=item.get("image", {}).get("contextLink", item.get("link", "")),
                    title=item.get("title", ""),
                    source=item.get("displayLink", "Google CSE"),
                    image_url=item.get("link"),
                    text=item.get("snippet", ""),
                    metadata={"mime": item.get("mime")},
                )
            )
        return results
