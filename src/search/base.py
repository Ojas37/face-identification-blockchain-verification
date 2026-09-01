"""Abstract base class for web and social search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from src.pipeline.models import SearchResult


class SearchError(Exception):
    """Exception raised when a search provider fails."""
    pass


class SearchProvider(ABC):
    """Abstract interface for discovery search providers."""

    @abstractmethod
    def search_by_image(self, image_path: Path, max_results: int = 10) -> List[SearchResult]:
        """
        Perform reverse image search using the input face image.

        Args:
            image_path: Path to the query image on local disk.
            max_results: Maximum number of search results to return.

        Returns:
            List of SearchResult objects.
        """
        pass

    @abstractmethod
    def search_by_query(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        Perform query-based search for web/social discovery.

        Args:
            query: Text query string.
            max_results: Maximum number of search results to return.

        Returns:
            List of SearchResult objects.
        """
        pass
