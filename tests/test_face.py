"""Unit tests for Face Detection and Image Utilities (Phase 2)."""

from pathlib import Path
import cv2
import numpy as np
import pytest

from src.face.base import DetectedFace
from src.face.detector import YuNetFaceDetector, FaceDetectionError
from src.utils.image_utils import load_image, compute_image_sha256, ImageLoadError


@pytest.fixture
def blank_image():
    """Create a 300x300 blank RGB image with no faces."""
    return np.zeros((300, 300, 3), dtype=np.uint8)


@pytest.fixture
def sample_face_image():
    """Load or generate a sample image."""
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    # Simple skin-tone oval with dark eye dots to test basic processing
    cv2.ellipse(img, (200, 200), (80, 110), 0, 0, 360, (180, 210, 240), -1)
    return img


def test_load_image_valid(tmp_path, blank_image):
    """Test safe image loading on a valid image file."""
    test_file = tmp_path / "valid.png"
    cv2.imwrite(str(test_file), blank_image)

    loaded = load_image(test_file)
    assert loaded is not None
    assert loaded.shape == (300, 300, 3)


def test_load_image_missing():
    """Test loading a nonexistent image file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_image("nonexistent_path_to_image_12345.jpg")


def test_load_image_corrupted(tmp_path):
    """Test loading a corrupted/empty file raises ImageLoadError."""
    corrupted_file = tmp_path / "corrupted.jpg"
    corrupted_file.write_text("not an image")

    with pytest.raises(ImageLoadError):
        load_image(corrupted_file)


def test_compute_image_sha256(tmp_path, blank_image):
    """Test image SHA-256 calculation."""
    test_file = tmp_path / "hash_test.png"
    cv2.imwrite(str(test_file), blank_image)

    digest1 = compute_image_sha256(test_file)
    digest2 = compute_image_sha256(blank_image)
    assert isinstance(digest1, str)
    assert len(digest1) == 64
    assert isinstance(digest2, str)
    assert len(digest2) == 64


def test_face_detector_no_face(blank_image):
    """Test detector returns empty list when no faces are present."""
    detector = YuNetFaceDetector()
    faces = detector.detect(blank_image)
    assert isinstance(faces, list)
    assert len(faces) == 0


def test_target_face_selection():
    """Test deterministic selection of target face based on area and confidence."""
    detector = YuNetFaceDetector()

    face1 = DetectedFace(bbox=(0, 0, 50, 50), confidence=0.9)   # area: 2500, score: 2250
    face2 = DetectedFace(bbox=(0, 0, 100, 100), confidence=0.8) # area: 10000, score: 8000
    face3 = DetectedFace(bbox=(0, 0, 80, 80), confidence=0.5)   # area: 6400, score: 3200

    selected = detector.select_target_face([face1, face2, face3])
    assert selected is not None
    assert selected == face2  # face2 has highest area * confidence score

    assert detector.select_target_face([]) is None


def test_sface_encoder_embedding_and_similarity(sample_face_image):
    """Test SFace face encoder extraction, dimension, L2 normalization, and similarity."""
    from src.face.encoder import SFaceEncoder
    from src.face.base import FaceEmbedding

    encoder = SFaceEncoder()
    face = DetectedFace(bbox=(100, 100, 200, 200), confidence=0.95)

    embedding1 = encoder.encode(sample_face_image, face)
    assert isinstance(embedding1, FaceEmbedding)
    assert embedding1.dimension == 128
    assert embedding1.vector.shape == (128,)

    # Verify L2 normalization
    norm = np.linalg.norm(embedding1.vector)
    assert np.isclose(norm, 1.0, atol=1e-5)

    # Identical embedding comparison should produce similarity ~ 1.0
    sim_self = encoder.compute_similarity(embedding1, embedding1)
    assert np.isclose(sim_self, 1.0, atol=1e-5)

    # Orthogonal / different embedding
    diff_vector = np.roll(embedding1.vector, 64)
    embedding2 = FaceEmbedding(vector=diff_vector)
    sim_diff = encoder.compute_similarity(embedding1, embedding2)
    assert sim_diff < 0.99
