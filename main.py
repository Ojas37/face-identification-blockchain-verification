#!/usr/bin/env python3
"""
Face Identification & Blockchain Verification Pipeline CLI Entry Point.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import settings
from src.pipeline.orchestrator import PipelineOrchestrator, PipelineExecutionError
from src.utils.logger import logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Face Identification & Blockchain Verification Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Primary reverse image search (using SerpApi Google Lens)
  python main.py --image data/input/person.jpg

  # Query-assisted search using DuckDuckGo
  python main.py --image data/input/person.jpg --provider duckduckgo --query "Person Name"

  # Custom similarity threshold and max candidates
  python main.py --image data/input/person.jpg --threshold 0.40 --max-candidates 5
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
    parser.add_argument(
        "--no-tamper-test",
        action="store_true",
        help="Skip the automated Phase 13 tamper demonstration",
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI execution routine."""
    args = parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        logger.error(f"Input image file not found: {image_path}")
        return 1

    try:
        orchestrator = PipelineOrchestrator(
            search_provider_name=args.provider,
            similarity_threshold=args.threshold,
            max_candidates=args.max_candidates,
        )

        results = orchestrator.execute(
            image_path=image_path,
            query=args.query,
            run_tamper_test=not args.no_tamper_test,
        )
        return 0 if results.get("verification_status") == "VERIFIED" else 1

    except PipelineExecutionError as e:
        logger.error(f"\n[PIPELINE ERROR] {e}")
        return 1
    except Exception as e:
        logger.error(f"\n[FATAL ERROR] Unexpected exception during execution: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
