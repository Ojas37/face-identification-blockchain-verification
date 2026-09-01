"""Candidate post collection, metadata extraction, and safe image downloading."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests

from src.config import settings
from src.pipeline.models import CandidatePost, SearchResult
from src.utils.image_utils import compute_image_sha256
from src.utils.logger import logger


class CandidateCollector:
    """
    Collects, enriches, deduplicates, and caches candidate posts and their images.
    Captures immutable provenance metadata (retrieved_at, source, image_sha256).
    """

    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 10) -> None:
        self.cache_dir = cache_dir or settings.candidates_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _extract_page_metadata(self, url: str) -> Dict[str, str]:
        """Fetch web page and extract OpenGraph and standard HTML metadata."""
        meta: Dict[str, str] = {}
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout, stream=True)
            # Limit page download to 2MB to avoid huge payload downloads
            content_sample = resp.raw.read(2 * 1024 * 1024, decode_content=True)
            soup = BeautifulSoup(content_sample, "html.parser")

            # Extract OpenGraph tags
            og_title = soup.find("meta", property="og:title")
            og_desc = soup.find("meta", property="og:description")
            og_image = soup.find("meta", property="og:image")
            og_site = soup.find("meta", property="og:site_name")

            if og_title and og_title.get("content"):
                meta["og_title"] = og_title["content"].strip()
            if og_desc and og_desc.get("content"):
                meta["og_description"] = og_desc["content"].strip()
            if og_image and og_image.get("content"):
                meta["og_image"] = og_image["content"].strip()
            if og_site and og_site.get("content"):
                meta["og_site_name"] = og_site["content"].strip()

            if not meta.get("og_title") and soup.title and soup.title.string:
                meta["og_title"] = soup.title.string.strip()

        except Exception as e:
            logger.debug(f"Could not extract metadata from {url}: {e}")

        return meta

    def _download_candidate_image(self, image_url: str, candidate_id: str) -> Optional[Path]:
        """Safely download candidate image with size limits and mime verification."""
        try:
            resp = requests.get(
                image_url,
                headers=self.headers,
                timeout=self.timeout,
                stream=True,
            )
            if resp.status_code != 200:
                return None

            content_type = resp.headers.get("Content-Type", "")
            if content_type and not ("image" in content_type or "octet-stream" in content_type):
                logger.debug(f"Skipping non-image content type: {content_type} from {image_url}")
                return None

            # Read content up to 10MB
            raw_bytes = bytearray()
            for chunk in resp.iter_content(chunk_size=65536):
                raw_bytes.extend(chunk)
                if len(raw_bytes) > 10 * 1024 * 1024:  # 10MB limit
                    logger.warning(f"Candidate image exceeded 10MB limit: {image_url}")
                    return None

            if len(raw_bytes) < 100:
                return None

            # Save to cache directory
            extension = ".jpg"
            if ".png" in image_url.lower():
                extension = ".png"
            elif ".webp" in image_url.lower():
                extension = ".webp"

            dest_path = self.cache_dir / f"cand_{candidate_id}{extension}"
            with open(dest_path, "wb") as f:
                f.write(raw_bytes)

            return dest_path
        except Exception as e:
            logger.debug(f"Failed to download image {image_url}: {e}")
            return None

    def collect(self, search_results: List[SearchResult]) -> List[CandidatePost]:
        """
        Transform raw SearchResults into normalized CandidatePost instances with cached media.

        Args:
            search_results: Raw results from SearchProvider.

        Returns:
            List of deduplicated CandidatePost objects.
        """
        candidates: List[CandidatePost] = []
        seen_urls = set()
        seen_hashes = set()

        for idx, item in enumerate(search_results):
            if not item.url or item.url in seen_urls:
                continue
            seen_urls.add(item.url)

            # Generate stable deterministic candidate ID
            cand_id = hashlib.sha256(f"{item.url}_{idx}".encode("utf-8")).hexdigest()[:16]

            # Domain source extraction
            parsed = urlparse(item.url)
            source_domain = item.source or parsed.netloc or "web"

            # Enrich with page metadata if available
            page_meta = self._extract_page_metadata(item.url)
            title = page_meta.get("og_title") or item.title or "Discovered Post"
            text = page_meta.get("og_description") or item.text or title
            image_url = item.image_url or page_meta.get("og_image") or ""

            local_image_path = None
            img_hash = ""

            if image_url:
                local_image_path = self._download_candidate_image(image_url, cand_id)
                if local_image_path and local_image_path.exists():
                    img_hash = compute_image_sha256(local_image_path)

            if img_hash and img_hash in seen_hashes:
                continue
            if img_hash:
                seen_hashes.add(img_hash)

            # Capture retrieved_at timestamp STRICTLY ONCE at collection time
            retrieved_at_timestamp = datetime.now(timezone.utc).isoformat()

            candidate = CandidatePost(
                id=cand_id,
                source=source_domain,
                url=item.url,
                title=title,
                text=text,
                image_url=image_url,
                image_sha256=img_hash,
                retrieved_at=retrieved_at_timestamp,
                local_image_path=local_image_path,
                metadata={**item.metadata, **page_meta},
            )
            candidates.append(candidate)

        logger.info(f"[COLLECTOR] Collected and cached {len(candidates)} unique candidates.")
        return candidates
