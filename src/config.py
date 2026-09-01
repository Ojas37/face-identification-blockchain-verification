"""Configuration and environment management module with fail-fast validation."""

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


class ConfigurationError(ValueError):
    """Exception raised when required configuration or environment variables are missing."""
    pass


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

    def validate_search_config(self, provider: Optional[str] = None) -> None:
        """Fail fast if required search credentials for the specified provider are missing."""
        selected_provider = provider or self.search_provider
        if selected_provider == "serpapi_lens":
            if not self.serpapi_api_key or self.serpapi_api_key.strip() == "" or self.serpapi_api_key.startswith("your_"):
                raise ConfigurationError(
                    "Missing required environment variable: SERPAPI_API_KEY\n"
                    "Please set a valid SERPAPI_API_KEY in your .env file to enable reverse image search.\n"
                    "Get your key from: https://serpapi.com/manage-api-key"
                )
        elif selected_provider == "google_cse":
            missing = []
            if not self.google_cse_api_key or self.google_cse_api_key.startswith("your_"):
                missing.append("GOOGLE_CSE_API_KEY")
            if not self.google_cse_engine_id or self.google_cse_engine_id.startswith("your_"):
                missing.append("GOOGLE_CSE_ENGINE_ID")
            if missing:
                raise ConfigurationError(
                    f"Missing required environment variable(s) for Google CSE: {', '.join(missing)}\n"
                    "Please set them in your .env file."
                )

    def validate_blockchain_config(self) -> None:
        """Fail fast if required blockchain credentials or parameters are missing."""
        if not self.blockchain_rpc_url or self.blockchain_rpc_url.strip() == "":
            raise ConfigurationError(
                "Missing required environment variable: BLOCKCHAIN_RPC_URL\n"
                "Please configure a valid EVM JSON-RPC URL in your .env file (e.g., http://127.0.0.1:8545 for Anvil)."
            )

        if not self.blockchain_private_key or self.blockchain_private_key.strip() == "" or self.blockchain_private_key.startswith("your_"):
            raise ConfigurationError(
                "Missing required environment variable: BLOCKCHAIN_PRIVATE_KEY\n"
                "Please configure a valid EVM account private key in your .env file to sign transactions."
            )

        # Validate private key format
        key = self.blockchain_private_key.strip()
        clean_key = key[2:] if key.startswith("0x") else key
        if len(clean_key) != 64:
            raise ConfigurationError(
                f"Invalid BLOCKCHAIN_PRIVATE_KEY format: expected 64 hexadecimal characters (or 66 with 0x prefix), got {len(key)} chars."
            )


# Singleton configuration instance
settings = Settings()
settings.ensure_directories()
