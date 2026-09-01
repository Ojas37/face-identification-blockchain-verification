#!/usr/bin/env python3
"""
Face Identification & Blockchain Verification Pipeline CLI Entry Point.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import settings
from src.utils.logger import logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Face Identification & Blockchain Verification Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python main.py --image data/input/sample.jpg
  python main.py --image data/input/sample.jpg --provider serpapi_lens
  python main.py --image data/input/sample.jpg --query "Sample Person"
        """,
    )
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        required=True,
        help="Path to the input face image (e.g. data/input/person.jpg)",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=None,
        help="Optional text query for query-assisted search provider augmentation",
    )
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        choices=["serpapi_lens", "duckduckgo", "google_cse"],
        default=settings.search_provider,
        help=f"Search provider for discovery (default: {settings.search_provider})",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=settings.match_similarity_threshold,
        help=f"Cosine similarity matching threshold (default: {settings.match_similarity_threshold})",
    )
    parser.add_argument(
        "--max-candidates",
        "-m",
        type=int,
        default=settings.max_candidates,
        help=f"Max candidates to retrieve and evaluate (default: {settings.max_candidates})",
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI execution routine."""
    args = parse_args()

    logger.info("=" * 60)
    logger.info("FACE IDENTIFICATION & BLOCKCHAIN VERIFICATION PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Target Image:      {args.image}")
    logger.info(f"Search Provider:   {args.provider}")
    logger.info(f"Match Threshold:   {args.threshold}")
    logger.info(f"Max Candidates:    {args.max_candidates}")
    if args.query:
        logger.info(f"Optional Query:    {args.query}")
    logger.info("=" * 60)

    # Skeleton validation
    image_path = Path(args.image)
    if not image_path.exists():
        logger.error(f"Input image file not found: {image_path}")
        return 1

    logger.info("[PHASE 1] Environment and project skeleton initialized successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
