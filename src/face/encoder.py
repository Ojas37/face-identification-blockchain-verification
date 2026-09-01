"""OpenCV SFace Face Feature Embedding and Recognition module."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import cv2
import numpy as np

from src.config import settings
from src.face.base import BaseFaceEncoder, DetectedFace, FaceEmbedding
from src.utils.logger import logger


class FaceEncodingError(Exception):
    """Exception raised when face encoding fails."""
    pass


class SFaceEncoder(BaseFaceEncoder):
    """
    OpenCV SFace deep-learning face recognizer.
    Extracts 128-dimensional L2-normalized facial embeddings.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        cosine_threshold: Optional[float] = None,
    ) -> None:
        """
        Initialize SFace face recognizer.

        Args:
            model_path: Path to the SFace ONNX model file.
            cosine_threshold: Cosine similarity threshold (~0.363 for SFace).
        """
        if model_path is None:
            model_path = settings.models_dir / "face_recognition_sface_2021dec.onnx"

        self.model_path = Path(model_path)
        self.cosine_threshold = (
            cosine_threshold
            if cosine_threshold is not None
            else settings.match_similarity_threshold
        )

        self._ensure_model_file()
        self._init_recognizer()

    def _ensure_model_file(self) -> None:
        """Ensure model file exists; trigger downloader if missing."""
        if not self.model_path.exists() or self.model_path.stat().st_size == 0:
            logger.info(f"SFace model not found at {self.model_path}. Attempting download...")
            from scripts.download_models import ensure_models
            if not ensure_models() or not self.model_path.exists():
                raise FaceEncodingError(
                    f"SFace ONNX model is missing at {self.model_path} and automated download failed."
                )

    def _init_recognizer(self) -> None:
        """Instantiate cv2.FaceRecognizerSF."""
        try:
            self.recognizer = cv2.FaceRecognizerSF.create(
                model=str(self.model_path),
                config="",
                backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
                target_id=cv2.dnn.DNN_TARGET_CPU,
            )
        except Exception as e:
            raise FaceEncodingError(f"Failed to initialize cv2.FaceRecognizerSF: {e}") from e

    def _prepare_raw_detection(self, face: DetectedFace) -> np.ndarray:
        """Ensure face has 15-element raw detection array needed for OpenCV alignCrop."""
        if face.raw_detection is not None and len(face.raw_detection) >= 15:
            return face.raw_detection

        x, y, w, h = face.bbox
        arr = np.zeros(15, dtype=np.float32)
        arr[0:4] = [x, y, w, h]
        if face.landmarks is not None and face.landmarks.shape == (5, 2):
            arr[4:14] = face.landmarks.flatten()
        else:
            # Synthetic landmarks if none provided: eye centers, nose center, mouth corners
            arr[4:6] = [x + w * 0.3, y + h * 0.35]  # right eye
            arr[6:8] = [x + w * 0.7, y + h * 0.35]  # left eye
            arr[8:10] = [x + w * 0.5, y + h * 0.55]  # nose
            arr[10:12] = [x + w * 0.35, y + h * 0.75]  # right mouth
            arr[12:14] = [x + w * 0.65, y + h * 0.75]  # left mouth
        arr[14] = face.confidence
        return arr

    def align_face(self, image: np.ndarray, face: DetectedFace) -> np.ndarray:
        """
        Align and crop face into standardized 112x112 representation.

        Args:
            image: Original BGR image array.
            face: DetectedFace instance.

        Returns:
            112x112 BGR aligned face crop.
        """
        if image is None or image.size == 0:
            raise FaceEncodingError("Cannot align face on empty or None image.")

        raw_det = self._prepare_raw_detection(face)
        try:
            aligned = self.recognizer.alignCrop(image, raw_det)
            if aligned is None or aligned.size == 0:
                raise FaceEncodingError("Face alignment produced empty crop.")
            return aligned
        except Exception as e:
            raise FaceEncodingError(f"Face alignment failed: {e}") from e

    def encode(self, image: np.ndarray, face: DetectedFace) -> FaceEmbedding:
        """
        Extract 128D feature embedding vector from detected face.

        Args:
            image: Original BGR image array.
            face: DetectedFace instance.

        Returns:
            FaceEmbedding instance.
        """
        aligned = self.align_face(image, face)
        try:
            raw_feature = self.recognizer.feature(aligned)
            if raw_feature is None or raw_feature.size == 0:
                raise FaceEncodingError("Feature extraction returned empty vector.")

            # SFace returns (1, 128) float32 vector
            vec = np.squeeze(raw_feature).astype(np.float32)
            # Ensure L2 normalization: ||v|| = 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

            return FaceEmbedding(vector=vec, dimension=len(vec))
        except Exception as e:
            raise FaceEncodingError(f"Face feature extraction failed: {e}") from e

    def compute_similarity(self, embedding1: FaceEmbedding, embedding2: FaceEmbedding) -> float:
        """
        Compute cosine similarity between two 128D face embeddings.
        Cosine similarity: (u . v) / (||u|| * ||v||)

        Returns:
            Cosine similarity score (-1.0 to 1.0).
        """
        u = embedding1.vector
        v = embedding2.vector
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        if norm_u == 0 or norm_v == 0:
            return 0.0
        cosine_sim = float(np.dot(u, v) / (norm_u * norm_v))
        return float(np.clip(cosine_sim, -1.0, 1.0))
