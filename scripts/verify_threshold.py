#!/usr/bin/env python3
"""
Threshold Verification Utility.
Compares two local face images, extracts SFace 128D embeddings,
and calculates cosine similarity and L2 distance to calibrate MATCH_SIMILARITY_THRESHOLD.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
from src.config import settings
from src.face.detector import YuNetFaceDetector
from src.face.encoder import SFaceEncoder
from src.utils.image_utils import load_image
from src.utils.logger import logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify face detection, SFace encoding, and similarity between two images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two images of the same person
  python scripts/verify_threshold.py --image1 data/input/person1_a.jpg --image2 data/input/person1_b.jpg

  # Compare two images of different people
  python scripts/verify_threshold.py --image1 data/input/person1.jpg --image2 data/input/person2.jpg --threshold 0.363
        """,
    )
    parser.add_argument(
        "--image1",
        "-1",
        type=str,
        required=True,
        help="Path to the first image file",
    )
    parser.add_argument(
        "--image2",
        "-2",
        type=str,
        required=True,
        help="Path to the second image file",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=settings.match_similarity_threshold,
        help=f"Cosine similarity threshold to evaluate against (default: {settings.match_similarity_threshold})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    path1 = Path(args.image1)
    path2 = Path(args.image2)

    if not path1.exists():
        logger.error(f"Image 1 not found: {path1}")
        return 1
    if not path2.exists():
        logger.error(f"Image 2 not found: {path2}")
        return 1

    logger.info("=" * 65)
    logger.info("FACE EMBEDDING & THRESHOLD VERIFICATION UTILITY")
    logger.info("=" * 65)
    logger.info(f"Image 1:   {path1}")
    logger.info(f"Image 2:   {path2}")
    logger.info(f"Threshold: {args.threshold:.4f} (Cosine Similarity)")
    logger.info("=" * 65)

    detector = YuNetFaceDetector()
    encoder = SFaceEncoder(cosine_threshold=args.threshold)

    # 1. Process Image 1
    logger.info(f"\n[IMAGE 1] Processing: {path1.name}")
    img1 = load_image(path1)
    faces1 = detector.detect(img1)
    if not faces1:
        logger.error(f"No face detected in Image 1: {path1}")
        return 1
    face1 = detector.select_target_face(faces1)
    logger.info(f"✓ Detected {len(faces1)} face(s). Selected bbox: {face1.bbox}, conf: {face1.confidence:.3f}")
    emb1 = encoder.encode(img1, face1)
    logger.info(f"✓ Extracted 128D embedding. Norm: {np.linalg.norm(emb1.vector):.4f}")

    # 2. Process Image 2
    logger.info(f"\n[IMAGE 2] Processing: {path2.name}")
    img2 = load_image(path2)
    faces2 = detector.detect(img2)
    if not faces2:
        logger.error(f"No face detected in Image 2: {path2}")
        return 1
    face2 = detector.select_target_face(faces2)
    logger.info(f"✓ Detected {len(faces2)} face(s). Selected bbox: {face2.bbox}, conf: {face2.confidence:.3f}")
    emb2 = encoder.encode(img2, face2)
    logger.info(f"✓ Extracted 128D embedding. Norm: {np.linalg.norm(emb2.vector):.4f}")

    # 3. Compute Metrics
    cosine_sim = encoder.compute_similarity(emb1, emb2)
    l2_dist = float(np.linalg.norm(emb1.vector - emb2.vector))
    is_match = cosine_sim >= args.threshold

    logger.info("\n" + "=" * 65)
    logger.info("SIMILARITY METRICS & CALIBRATION REPORT")
    logger.info("=" * 65)
    logger.info(f"Cosine Similarity:       {cosine_sim:+.6f}  (Range: -1.0 to +1.0, Higher is closer)")
    logger.info(f"L2 (Euclidean) Distance: {l2_dist:.6f}   (Range: 0.0 to 2.0, Lower is closer)")
    logger.info(f"Evaluated Threshold:     {args.threshold:.6f}")
    logger.info(f"Match Decision:          {'SAME PERSON (MATCH ✓)' if is_match else 'DIFFERENT PERSON (NO MATCH ✗)'}")
    logger.info("-" * 65)
    logger.info("OPENCV SFACE BASELINE REFERENCE THRESHOLDS:")
    logger.info("  - OpenCV Default Cosine Threshold:  0.363  (Optimal for open-set identification)")
    logger.info("  - OpenCV Default L2 Distance:       1.128  (Scores <= 1.128 are same person)")
    logger.info("  - High-Precision Cosine Threshold:  0.500+ (Stricter matching, lower false positives)")
    logger.info("=" * 65 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
