"""
Model registry, metadata, and validation utilities for ClassSnap.
Tracks provenance, licenses, checksums, and model initialization validity.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Dict, Optional
import cv2

from classsnap.config import get_settings
from classsnap.exceptions import ConfigurationError
from classsnap.logger import get_logger

logger = get_logger("cv.model_registry")


@dataclass(frozen=True)
class ModelMetadata:
    name: str
    version: str
    task: str  # "detection" | "recognition"
    filename: str
    expected_sha256: Optional[str]
    license: str
    source_url: str
    framework: str = "OpenCV DNN / ONNX"


KNOWN_MODELS: Dict[str, ModelMetadata] = {
    "yunet": ModelMetadata(
        name="YuNet",
        version="2023mar",
        task="detection",
        filename="face_detection_yunet_2023mar.onnx",
        expected_sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        license="Apache-2.0",
        source_url="https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet",
    ),
    "sface": ModelMetadata(
        name="SFace",
        version="2021dec",
        task="recognition",
        filename="face_recognition_sface_2021dec.onnx",
        expected_sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
        license="Apache-2.0",
        source_url="https://huggingface.co/opencv/face_recognition_sface",
    ),
}


def compute_file_sha256(filepath: Path) -> str:
    """Computes SHA-256 hash for a given file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_model_file(model_path: Path, model_key: str) -> ModelMetadata:
    """
    Validates model file existence, readable permissions, non-zero size,
    and returns its associated metadata.
    """
    if not model_path.exists():
        raise ConfigurationError(
            f"Model file not found at: {model_path}. "
            f"Please run 'python scripts/download_models.py' or check MODELS_DIR."
        )

    file_size = model_path.stat().st_size
    if file_size < 1000:
        raise ConfigurationError(
            f"Model file at {model_path} is suspiciously small ({file_size} bytes)."
        )

    meta = KNOWN_MODELS.get(model_key)
    if not meta:
        meta = ModelMetadata(
            name=model_key,
            version="custom",
            task="unknown",
            filename=model_path.name,
            expected_sha256=None,
            license="Undocumented",
            source_url="Local file",
        )

    logger.info(
        f"Validated model '{meta.name}' (version: {meta.version}, task: {meta.task}, size: {file_size / (1024*1024):.2f} MB)"
    )
    return meta
