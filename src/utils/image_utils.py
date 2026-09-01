"""Image utility functions for safe loading, validation, and checksum calculation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union
import cv2
import numpy as np


class ImageLoadError(Exception):
    """Exception raised when an image cannot be loaded or decoded."""
    pass


def load_image(image_path: Union[str, Path]) -> np.ndarray:
    """
    Safely load an image from disk and validate decoding and dimensions.

    Args:
        image_path: Path to the image file.

    Returns:
        Decoded image as a NumPy BGR array (uint8).

    Raises:
        FileNotFoundError: If the file does not exist.
        ImageLoadError: If the image file is corrupted or cannot be decoded.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file does not exist: {path}")

    if not path.is_file():
        raise ImageLoadError(f"Target path is not a file: {path}")

    # Read image using OpenCV
    image = cv2.imread(str(path))
    if image is None:
        raise ImageLoadError(f"Failed to decode image (unsupported or corrupted format): {path}")

    if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
        raise ImageLoadError(f"Image has invalid dimensions: {image.shape}")

    return image


def compute_image_sha256(image_source: Union[str, Path, bytes, np.ndarray]) -> str:
    """
    Compute cryptographic SHA-256 hash of an image file, raw bytes, or image array.

    Args:
        image_source: Path to image file, raw bytes, or NumPy image array.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    if isinstance(image_source, (str, Path)):
        path = Path(image_source)
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    elif isinstance(image_source, bytes):
        return hashlib.sha256(image_source).hexdigest()
    elif isinstance(image_source, np.ndarray):
        # Encode as JPEG or PNG bytes for consistent checksum
        success, encoded = cv2.imencode(".png", image_source)
        if not success:
            raise ValueError("Failed to encode image array to bytes for hashing.")
        return hashlib.sha256(encoded.tobytes()).hexdigest()
    else:
        raise TypeError(f"Unsupported image source type: {type(image_source)}")
