"""Script to download pretrained OpenCV Zoo ONNX models for face detection (YuNet) and recognition (SFace)."""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.utils.logger import logger

MODEL_URLS = {
    "face_detection_yunet_2023mar.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}


def download_file(url: str, destination: Path) -> bool:
    """Download a file with progress reporting."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        logger.info(f"Model already exists at: {destination} ({destination.stat().st_size} bytes)")
        return True

    logger.info(f"Downloading {destination.name} from {url}...")
    try:
        urllib.request.urlretrieve(url, destination)
        logger.info(f"✓ Downloaded {destination.name} ({destination.stat().st_size} bytes)")
        return True
    except Exception as e:
        logger.error(f"Failed to download {destination.name}: {e}")
        return False


def ensure_models() -> bool:
    """Ensure all required ONNX models are present in the models directory."""
    models_dir = settings.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    success = True
    for filename, url in MODEL_URLS.items():
        dest = models_dir / filename
        if not download_file(url, dest):
            success = False
    return success


if __name__ == "__main__":
    if ensure_models():
        logger.info("All required face models are ready.")
        sys.exit(0)
    else:
        logger.error("Failed to download one or more face models.")
        sys.exit(1)
