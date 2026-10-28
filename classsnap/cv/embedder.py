"""
OpenCV SFace feature embedding extraction implementation for ClassSnap.
Extracts 128-dimensional normalized facial feature vectors.
"""

from pathlib import Path
from typing import Union
import cv2
import numpy as np

from classsnap.cv.base import EmbeddingExtractor
from classsnap.cv.model_registry import validate_model_file
from classsnap.exceptions import BiometricProcessingError, ConfigurationError
from classsnap.logger import get_logger

logger = get_logger("cv.embedder")


class SFaceEmbeddingExtractor(EmbeddingExtractor):
    """
    Face recognizer wrapping OpenCV SFace (ONNX model).
    Produces normalized 128-dimensional float32 feature embeddings.
    """

    def __init__(self, model_path: Union[str, Path]):
        self.model_path = Path(model_path)
        self.metadata = validate_model_file(self.model_path, "sface")

        try:
            self._recognizer = cv2.FaceRecognizerSF.create(
                model=str(self.model_path),
                config="",
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize OpenCV SFace recognizer from {self.model_path}: {e}"
            )

    @property
    def model_name(self) -> str:
        return self.metadata.name

    @property
    def model_version(self) -> str:
        return self.metadata.version

    @property
    def embedding_dimension(self) -> int:
        return 128

    def extract_embedding(self, face_image: np.ndarray) -> np.ndarray:
        """
        Extracts a 128D unit-normalized feature embedding from an aligned face image.
        Input image must be a 3-channel BGR numpy array.
        """
        if face_image is None or not isinstance(face_image, np.ndarray) or face_image.size == 0:
            raise BiometricProcessingError("Face image is invalid or empty for embedding extraction")

        if len(face_image.shape) != 3 or face_image.shape[2] != 3:
            raise BiometricProcessingError(
                f"Face image must be 3-channel BGR, got shape: {face_image.shape}"
            )

        # SFace expects 112x112 input
        if face_image.shape[:2] != (112, 112):
            face_image = cv2.resize(face_image, (112, 112), interpolation=cv2.INTER_LINEAR)

        try:
            raw_feature = self._recognizer.feature(face_image)
        except Exception as e:
            logger.error(f"SFace feature extraction failed: {e}")
            raise BiometricProcessingError(f"Embedding extraction failed: {e}")

        # Flatten to 1D vector
        embedding = raw_feature.flatten().astype(np.float32)

        # Ensure unit L2 normalization: ||v|| = 1.0
        norm = float(np.linalg.norm(embedding))
        if norm > 1e-8:
            embedding = embedding / norm

        return embedding

    @staticmethod
    def compute_cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculates cosine similarity between two unit-normalized embeddings.
        Returns similarity score in [-1.0, 1.0].
        """
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 < 1e-8 or norm2 < 1e-8:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))
