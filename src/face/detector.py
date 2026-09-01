"""OpenCV YuNet Face Detector implementation."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np

from src.config import settings
from src.face.base import BaseFaceDetector, DetectedFace
from src.utils.logger import logger


class FaceDetectionError(Exception):
    """Exception raised when face detection encounters a fatal error."""
    pass


class YuNetFaceDetector(BaseFaceDetector):
    """
    High-performance, lightweight deep-learning face detector using OpenCV YuNet ONNX.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        confidence_threshold: Optional[float] = None,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
    ) -> None:
        """
        Initialize the YuNet face detector.

        Args:
            model_path: Path to the YuNet ONNX model file.
            confidence_threshold: Minimum detection confidence score (0.0 - 1.0).
            nms_threshold: Non-Maximum Suppression threshold.
            top_k: Keep top-k bounding boxes before NMS.
        """
        if model_path is None:
            model_path = settings.models_dir / "face_detection_yunet_2023mar.onnx"

        self.model_path = Path(model_path)
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.face_detection_confidence
        )
        self.nms_threshold = nms_threshold
        self.top_k = top_k

        self._ensure_model_file()
        self._init_detector()

    def _ensure_model_file(self) -> None:
        """Check if model file exists; trigger download helper if missing."""
        if not self.model_path.exists() or self.model_path.stat().st_size == 0:
            logger.info(f"YuNet model not found at {self.model_path}. Attempting download...")
            from scripts.download_models import ensure_models
            if not ensure_models() or not self.model_path.exists():
                raise FaceDetectionError(
                    f"YuNet ONNX model is missing at {self.model_path} and automated download failed."
                )

    def _init_detector(self) -> None:
        """Instantiate cv2.FaceDetectorYN."""
        try:
            self.detector = cv2.FaceDetectorYN.create(
                model=str(self.model_path),
                config="",
                input_size=(320, 320),  # Placeholder, updated per image in detect()
                score_threshold=self.confidence_threshold,
                nms_threshold=self.nms_threshold,
                top_k=self.top_k,
                backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
                target_id=cv2.dnn.DNN_TARGET_CPU,
            )
        except Exception as e:
            raise FaceDetectionError(f"Failed to initialize cv2.FaceDetectorYN: {e}") from e

    def detect(self, image: np.ndarray) -> List[DetectedFace]:
        """
        Detect faces in the input image.

        Args:
            image: BGR image array (H, W, 3).

        Returns:
            List of detected faces with bounding boxes, confidence, and landmarks.
        """
        if image is None or image.size == 0:
            raise FaceDetectionError("Cannot perform face detection on empty or None image.")

        h, w = image.shape[:2]
        self.detector.setInputSize((w, h))

        try:
            _, detections = self.detector.detect(image)
        except Exception as e:
            raise FaceDetectionError(f"OpenCV YuNet face detection failed: {e}") from e

        faces: List[DetectedFace] = []
        if detections is None or len(detections) == 0:
            return faces

        for det in detections:
            # Layout of YuNet detection row (15 elements):
            # [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
            x, y, box_w, box_h = int(det[0]), int(det[1]), int(det[2]), int(det[3])
            score = float(det[-1])
            landmarks = det[4:14].reshape((5, 2))

            # Clamp coordinates to image boundaries
            x = max(0, x)
            y = max(0, y)
            box_w = min(box_w, w - x)
            box_h = min(box_h, h - y)

            if box_w > 0 and box_h > 0:
                faces.append(
                    DetectedFace(
                        bbox=(x, y, box_w, box_h),
                        confidence=score,
                        landmarks=landmarks,
                        raw_detection=det,
                    )
                )

        return faces
