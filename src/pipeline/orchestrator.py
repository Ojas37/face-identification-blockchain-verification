"""End-to-end pipeline orchestrator for Face Identification & Blockchain Verification."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.blockchain.client import BlockchainClient, BlockchainError
from src.config import settings
from src.face.detector import YuNetFaceDetector, FaceDetectionError
from src.face.encoder import SFaceEncoder, FaceEncodingError
from src.hashing.canonicalizer import canonicalize_post, to_canonical_json_string
from src.hashing.hasher import compute_content_hash, verify_content_hash
from src.matching.comparator import FaceComparator
from src.matching.ranker import CandidateRanker
from src.pipeline.models import CandidatePost, MatchResult, VerificationRecord
from src.search.base import SearchError, SearchProvider
from src.search.collector import CandidateCollector
from src.search.duckduckgo import DuckDuckGoSearchProvider
from src.search.google_cse import GoogleCSESearchProvider
from src.search.reverse_image import SerpApiLensSearchProvider
from src.utils.image_utils import load_image, ImageLoadError
from src.utils.logger import logger


class PipelineExecutionError(Exception):
    """Exception raised when pipeline execution fails."""
    pass


class PipelineOrchestrator:
    """
    Coordinates and executes the entire 14-phase pipeline from input face image
    to genuine web search, face matching, cryptographic hashing, blockchain recording,
    re-verification, and tamper testing.
    """

    def __init__(
        self,
        search_provider_name: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        max_candidates: Optional[int] = None,
        blockchain_client: Optional[BlockchainClient] = None,
    ) -> None:
        self.provider_name = search_provider_name or settings.search_provider
        self.threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else settings.match_similarity_threshold
        )
        self.max_candidates = max_candidates or settings.max_candidates

        # Initialize sub-modules
        self.detector = YuNetFaceDetector()
        self.encoder = SFaceEncoder(cosine_threshold=self.threshold)
        self.comparator = FaceComparator(
            detector=self.detector,
            encoder=self.encoder,
            threshold=self.threshold,
        )
        self.ranker = CandidateRanker(comparator=self.comparator)
        self.collector = CandidateCollector()
        self.blockchain = blockchain_client or BlockchainClient()

        # Initialize search provider
        self.search_provider = self._init_search_provider(self.provider_name)

    def _init_search_provider(self, name: str) -> SearchProvider:
        """Instantiate configured search provider."""
        if name == "serpapi_lens":
            return SerpApiLensSearchProvider()
        elif name == "duckduckgo":
            return DuckDuckGoSearchProvider()
        elif name == "google_cse":
            return GoogleCSESearchProvider()
        else:
            raise ValueError(f"Unknown search provider: {name}")

    def execute(
        self,
        image_path: Path,
        query: Optional[str] = None,
        run_tamper_test: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the full end-to-end verification pipeline.

        Args:
            image_path: Path to local target face image.
            query: Optional query string for query-assisted search providers.
            run_tamper_test: Whether to execute the tamper test demonstration.

        Returns:
            Dictionary containing complete pipeline results, transaction metadata, and audit log.
        """
        path = Path(image_path)
        logger.info("\n" + "=" * 60)
        logger.info("STARTING FACE IDENTIFICATION & BLOCKCHAIN VERIFICATION")
        logger.info("=" * 60)

        # -------------------------------------------------------------
        # PHASE 1 & 2: Input Image Loading & Face Detection
        # -------------------------------------------------------------
        logger.info("\n[PHASE 1 & 2] Loading Image and Detecting Faces...")
        try:
            image = load_image(path)
            logger.info(f"✓ Image loaded successfully ({image.shape[1]}x{image.shape[0]} px)")
        except (FileNotFoundError, ImageLoadError) as e:
            raise PipelineExecutionError(f"Image load failure: {e}") from e

        detected_faces = self.detector.detect(image)
        if not detected_faces:
            raise PipelineExecutionError(
                f"No face detected in input image: {path}. "
                "Ensure the image has adequate lighting and a clear visible face."
            )

        logger.info(f"✓ {len(detected_faces)} face(s) detected in input image.")
        target_face = self.detector.select_target_face(detected_faces)
        if not target_face:
            raise PipelineExecutionError("Target face selection failed.")

        logger.info(
            f"✓ Target face selected: bbox={target_face.bbox}, "
            f"confidence={target_face.confidence:.3f}"
        )

        # -------------------------------------------------------------
        # PHASE 3: Face Feature Encoding (128D Embedding)
        # -------------------------------------------------------------
        logger.info("\n[PHASE 3] Extracting Face Feature Embedding...")
        try:
            input_embedding = self.encoder.encode(image, target_face)
            logger.info(
                f"✓ Face embedding extracted: {input_embedding.dimension}D vector "
                f"(L2 normalized)"
            )
        except FaceEncodingError as e:
            raise PipelineExecutionError(f"Face encoding failure: {e}") from e

        # -------------------------------------------------------------
        # PHASE 4: Genuine Web / Social Media Discovery
        # -------------------------------------------------------------
        logger.info(f"\n[PHASE 4] Executing Genuine Web Search via '{self.provider_name}'...")
        try:
            if query:
                search_results = self.search_provider.search_by_query(
                    query, max_results=self.max_candidates
                )
            else:
                search_results = self.search_provider.search_by_image(
                    path, max_results=self.max_candidates
                )
        except SearchError as e:
            raise PipelineExecutionError(f"Search discovery failed: {e}") from e

        if not search_results:
            raise PipelineExecutionError(
                f"Search provider '{self.provider_name}' returned 0 candidate results."
            )

        logger.info(f"✓ Discovered {len(search_results)} candidate search result(s).")

        # -------------------------------------------------------------
        # PHASE 5: Candidate Collection & Immutable Provenance Capture
        # -------------------------------------------------------------
        logger.info("\n[PHASE 5] Collecting Candidates & Extracting Media Metadata...")
        candidates = self.collector.collect(search_results)
        if not candidates:
            raise PipelineExecutionError("Failed to collect any valid candidate posts.")

        logger.info(f"✓ Collected and cached {len(candidates)} unique candidate post(s).")

        # -------------------------------------------------------------
        # PHASE 6: Face Matching & Cosine Similarity Ranking
        # -------------------------------------------------------------
        logger.info("\n[PHASE 6] Matching Target Face against Candidates...")
        best_match, all_ranked = self.ranker.rank_candidates(input_embedding, candidates)

        if not best_match:
            highest_score = all_ranked[0].similarity_score if all_ranked else 0.0
            raise PipelineExecutionError(
                f"NO MATCH FOUND: None of the {len(candidates)} candidate(s) passed "
                f"the similarity threshold (Top score: {highest_score:.4f} < {self.threshold:.4f})."
            )

        matched_candidate = best_match.candidate
        logger.info(f"✓ MATCH FOUND! Best match: {matched_candidate.url}")
        logger.info(f"  Similarity Score: {best_match.similarity_score:.4f}")

        # -------------------------------------------------------------
        # PHASE 7 & 8: Data Canonicalization (RFC 8785) & SHA-256 Fingerprint
        # -------------------------------------------------------------
        logger.info("\n[PHASE 7 & 8] Normalizing Post Data & Generating SHA-256 Fingerprint...")
        canonical_bytes = canonicalize_post(matched_candidate)
        canonical_str = to_canonical_json_string(matched_candidate)
        content_hash = compute_content_hash(matched_candidate)

        logger.info(f"✓ Canonical JSON Representation:\n  {canonical_str}")
        logger.info(f"✓ SHA-256 Content Fingerprint: {content_hash}")

        # -------------------------------------------------------------
        # PHASE 9 & 10: EVM Blockchain Record Submission
        # -------------------------------------------------------------
        logger.info("\n[PHASE 9 & 10] Submitting Verification Record to Blockchain...")
        try:
            on_chain_record = self.blockchain.upload_record(
                content_hash=content_hash,
                source=matched_candidate.source,
                url=matched_candidate.url,
            )
            logger.info(f"✓ Record stored on-chain! TX: {on_chain_record.tx_hash}")
            logger.info(f"  Block Number: #{on_chain_record.block_number}")
            logger.info(f"  Recorded By:  {on_chain_record.recorder}")
        except BlockchainError as e:
            raise PipelineExecutionError(f"Blockchain submission failure: {e}") from e

        # -------------------------------------------------------------
        # PHASE 11: Blockchain Record Retrieval
        # -------------------------------------------------------------
        logger.info("\n[PHASE 11] Retrieving Verification Record from Blockchain...")
        try:
            retrieved_record = self.blockchain.retrieve_record(
                content_hash=content_hash,
                tx_hash=on_chain_record.tx_hash,
            )
            logger.info("✓ On-chain record retrieved successfully.")
            logger.info(f"  On-chain Hash: {retrieved_record.content_hash}")
        except BlockchainError as e:
            raise PipelineExecutionError(f"Blockchain retrieval failure: {e}") from e

        # -------------------------------------------------------------
        # PHASE 12: Local Re-Calculation & Cryptographic Verification
        # -------------------------------------------------------------
        logger.info("\n[PHASE 12] Re-calculating Local Hash & Verifying against Blockchain...")
        local_recalculated_hash = compute_content_hash(matched_candidate)

        is_verified = (local_recalculated_hash == retrieved_record.content_hash)
        if is_verified:
            logger.info("========================================")
            logger.info("✓ VERIFIED")
            logger.info("✓ Data fingerprint matches blockchain record")
            logger.info("✓ No detected modification")
            logger.info("========================================")
        else:
            logger.error("========================================")
            logger.error("✗ VERIFICATION FAILED")
            logger.error(
                f"✗ Local hash ({local_recalculated_hash}) != "
                f"Chain hash ({retrieved_record.content_hash})"
            )
            logger.error("========================================")
            raise PipelineExecutionError("Verification failed: Hash mismatch.")

        # -------------------------------------------------------------
        # PHASE 13: Tamper Test Demonstration
        # -------------------------------------------------------------
        tamper_status = "NOT_RUN"
        if run_tamper_test:
            logger.info("\n[PHASE 13] Executing Proof-of-Tamper Demonstration...")
            tampered_post = copy.deepcopy(matched_candidate)
            tampered_post.text = tampered_post.text + " [TAMPERED_INJECTED_CONTENT]"
            tampered_hash = compute_content_hash(tampered_post)

            logger.info(f"  Original Data Hash: {local_recalculated_hash}")
            logger.info(f"  Tampered Data Hash: {tampered_hash}")

            if tampered_hash != retrieved_record.content_hash:
                logger.info("✓ TAMPER TEST PASSED: Modified data correctly rejected.")
                tamper_status = "TAMPER_DETECTED"
            else:
                logger.error("✗ TAMPER TEST FAILED: Modified data unexpectedly matched hash!")
                tamper_status = "TAMPER_UNDETECTED"

        # -------------------------------------------------------------
        # PHASE 14: Final Summary Audit Report
        # -------------------------------------------------------------
        logger.info("\n" + "=" * 60)
        logger.info("FINAL RESULT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Face Match:              FOUND (Cosine Sim: {best_match.similarity_score:.4f})")
        logger.info(f"Matching Post URL:       {matched_candidate.url}")
        logger.info(f"Content SHA-256 Hash:    {content_hash}")
        logger.info(f"Blockchain Transaction:  {on_chain_record.tx_hash}")
        logger.info(f"Blockchain Block:        #{on_chain_record.block_number}")
        logger.info(f"Verification Status:     {'VERIFIED ✓' if is_verified else 'FAILED ✗'}")
        logger.info(f"Tamper Test Result:      {tamper_status}")
        logger.info("=" * 60 + "\n")

        return {
            "match_found": True,
            "matched_candidate": matched_candidate,
            "similarity_score": best_match.similarity_score,
            "content_hash": content_hash,
            "tx_hash": on_chain_record.tx_hash,
            "block_number": on_chain_record.block_number,
            "verification_status": "VERIFIED" if is_verified else "FAILED",
            "tamper_test_status": tamper_status,
        }
