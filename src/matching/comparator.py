"""Face comparison engine computing similarity between input face and candidate images."""

from __future__ import annotations

from typing import Optional
from src.config import settings
from src.face.base import BaseFaceDetector, BaseFaceEncoder, FaceEmbedding
from src.face.detector import YuNetFaceDetector
from src.face.encoder import SFaceEncoder
from src.pipeline.models import CandidatePost, MatchResult
from src.utils.image_utils import load_image, ImageLoadError
from src.utils.logger import logger


class FaceComparator:
    """
    Compares an input face embedding against faces detected in candidate post images.
    """

    def __init__(
        self,
        detector: Optional[BaseFaceDetector] = None,
        encoder: Optional[BaseFaceEncoder] = None,
        threshold: Optional[float] = None,
    ) -> None:
        self.detector = detector or YuNetFaceDetector()
        self.encoder = encoder or SFaceEncoder()
        self.threshold = (
            threshold
            if threshold is not None
            else settings.match_similarity_threshold
        )

    def compare_candidate(
        self,
        input_embedding: FaceEmbedding,
        candidate: CandidatePost,
    ) -> MatchResult:
        """
        Detect and encode faces in candidate image and compare against input embedding.

        Args:
            input_embedding: 128D FaceEmbedding of target person.
            candidate: CandidatePost with downloaded local image.

        Returns:
            MatchResult containing similarity score and verification status.
        """
        if not candidate.local_image_path or not candidate.local_image_path.exists():
            return MatchResult(
                candidate=candidate,
                similarity_score=0.0,
                is_match=False,
                threshold=self.threshold,
                details="No local image available for face detection",
            )

        try:
            cand_image = load_image(candidate.local_image_path)
        except (FileNotFoundError, ImageLoadError) as e:
            return MatchResult(
                candidate=candidate,
                similarity_score=0.0,
                is_match=False,
                threshold=self.threshold,
                details=f"Failed to decode candidate image: {e}",
            )

        detected_faces = self.detector.detect(cand_image)
        if not detected_faces:
            return MatchResult(
                candidate=candidate,
                similarity_score=0.0,
                is_match=False,
                threshold=self.threshold,
                details="No faces detected in candidate image",
            )

        # Compare against all detected faces in candidate image and take highest match
        max_similarity = -1.0
        best_face_idx = 0

        for idx, face in enumerate(detected_faces):
            try:
                face_emb = self.encoder.encode(cand_image, face)
                sim = self.encoder.compute_similarity(input_embedding, face_emb)
                if sim > max_similarity:
                    max_similarity = sim
                    best_face_idx = idx
            except Exception as e:
                logger.debug(f"Encoding error for face #{idx} in candidate {candidate.id}: {e}")

        is_match = max_similarity >= self.threshold
        details = (
            f"Evaluated {len(detected_faces)} face(s). "
            f"Highest cosine similarity: {max_similarity:.4f} "
            f"(threshold: {self.threshold:.4f})"
        )

        return MatchResult(
            candidate=candidate,
            similarity_score=max_similarity,
            is_match=is_match,
            threshold=self.threshold,
            details=details,
        )
