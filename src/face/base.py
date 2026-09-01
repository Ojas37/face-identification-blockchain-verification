"""Abstract base classes and data structures for face detection and encoding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np


@dataclass
class DetectedFace:
    """Represents a single face detected within an image."""
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    landmarks: Optional[np.ndarray] = None  # 5 facial landmarks (eyes, nose, mouth corners)
    raw_detection: Optional[np.ndarray] = None  # Raw detector output row

    @property
    def area(self) -> int:
        """Calculate bounding box area in pixels."""
        return self.bbox[2] * self.bbox[3]


class BaseFaceDetector(ABC):
    """Abstract interface for face detection backends."""

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[DetectedFace]:
        """
        Detect all faces within an image.

        Args:
            image: BGR image array (H, W, 3).

        Returns:
            List of DetectedFace instances.
        """
        pass

    def select_target_face(self, faces: List[DetectedFace]) -> Optional[DetectedFace]:
        """
        Deterministically select the most prominent/appropriate target face
        from a list of detected faces (e.g. largest bounding box area and highest confidence).

        Args:
            faces: List of detected faces.

        Returns:
            The selected target DetectedFace, or None if the list is empty.
        """
        if not faces:
            return None
        # Deterministic sorting: primary key is area * confidence, secondary is area
        return max(faces, key=lambda f: (f.area * f.confidence, f.area))
