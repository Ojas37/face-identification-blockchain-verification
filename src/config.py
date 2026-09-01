"""Configuration and environment management module."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Base directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from repository root if present
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Central settings and configuration values loaded from environment."""

    # Paths
    base_dir: Path = BASE_DIR
    models_dir: Path = field(
        default_factory=lambda: BASE_DIR / os.getenv("MODELS_DIR", "data/models")
    )
    candidates_cache_dir: Path = field(
        default_factory=lambda: BASE_DIR / os.getenv("CANDIDATES_CACHE_DIR", "data/candidates")
    )
    input_dir: Path = field(
        default_factory=lambda: BASE_DIR / "data/input"
    )

    # Face Detection & Matching Thresholds
    face_detection_confidence: float = field(
        default_factory=lambda: float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.8"))
    )
    match_similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv("MATCH_SIMILARITY_THRESHOLD", "0.363"))
    )

    # Search Configuration
    search_provider: str = field(
        default_factory=lambda: os.getenv("SEARCH_PROVIDER", "serpapi_lens")
    )
    max_candidates: int = field(
        default_factory=lambda: int(os.getenv("MAX_CANDIDATES", "10"))
    )
    serpapi_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("SERPAPI_API_KEY")
    )
    google_cse_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GOOGLE_CSE_API_KEY")
    )
    google_cse_engine_id: Optional[str] = field(
        default_factory=lambda: os.getenv("GOOGLE_CSE_ENGINE_ID")
    )

    # Blockchain Configuration (EVM / Web3)
    blockchain_rpc_url: str = field(
        default_factory=lambda: os.getenv("BLOCKCHAIN_RPC_URL", "http://127.0.0.1:8545")
    )
    blockchain_private_key: Optional[str] = field(
        default_factory=lambda: os.getenv("BLOCKCHAIN_PRIVATE_KEY")
    )
    registry_contract_address: Optional[str] = field(
        default_factory=lambda: os.getenv("REGISTRY_CONTRACT_ADDRESS")
    )
    blockchain_mode: str = field(
        default_factory=lambda: os.getenv("BLOCKCHAIN_MODE", "contract")
    )

    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )

    def ensure_directories(self) -> None:
        """Ensure that required runtime data directories exist."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_cache_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)


# Singleton configuration instance
settings = Settings()
settings.ensure_directories()
