"""Secondary search provider using DuckDuckGo Live Search API."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from duckduckgo_search import DDGS

from src.pipeline.models import SearchResult
from src.search.base import SearchError, SearchProvider
from src.utils.logger import logger


class DuckDuckGoSearchProvider(SearchProvider):
    """
    DuckDuckGo live search provider.
    Supports query-driven web and image searches without requiring paid API keys.
    """

    def __init__(self) -> None:
        self.ddgs = DDGS()

    def search_by_image(self, image_path: Path, max_results: int = 10) -> List[SearchResult]:
        """
        DuckDuckGo does not have a direct file upload reverse image API.
        Extracts filename context or falls back to prompt query.
        """
        query = Path(image_path).stem.replace("_", " ").replace("-", " ")
        logger.info(f"[SEARCH] DuckDuckGo query derived from image stem: '{query}'")
        return self.search_by_query(query, max_results=max_results)

    def search_by_query(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search DuckDuckGo for live web and image candidate results.
        """
        if not query or not query.strip():
            raise SearchError("Search query cannot be empty.")

        results: List[SearchResult] = []
        logger.info(f"[SEARCH] Querying DuckDuckGo live search for: '{query}'")

        try:
            # 1. Fetch image results
            image_items = self.ddgs.images(
                keywords=query,
                max_results=max_results,
            )
            for item in image_items:
                results.append(
                    SearchResult(
                        url=item.get("url", ""),
                        title=item.get("title", "DuckDuckGo Image"),
                        source=item.get("source", "DuckDuckGo"),
                        image_url=item.get("image", item.get("thumbnail")),
                        text=item.get("title", ""),
                        metadata={"width": item.get("width"), "height": item.get("height")},
                    )
                )

            # 2. If fewer than max_results images found, supplement with text web results
            if len(results) < max_results:
                text_items = self.ddgs.text(
                    keywords=query,
                    max_results=max_results - len(results),
                )
                for item in text_items:
                    results.append(
                        SearchResult(
                            url=item.get("href", ""),
                            title=item.get("title", "DuckDuckGo Web"),
                            source="DuckDuckGo",
                            image_url=None,
                            text=item.get("body", ""),
                            metadata={},
                        )
                    )

        except Exception as e:
            raise SearchError(f"DuckDuckGo live search failed: {e}") from e

        logger.info(f"[SEARCH] Discovered {len(results)} live results via DuckDuckGo.")
        return results[:max_results]
