"""
Centralized Configuration for ClassSnap using pydantic-settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ClassSnap"
    app_version: str = "0.1.0"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"

    # Security & Privacy
    secret_key: str = "dev-secret-key-change-in-production-classsnap-2026"
    cors_allowed_origins: str = "http://localhost:8000"
    photo_retention_days: int = 0
    auto_delete_temp_photos: bool = True

    # Database
    database_url: str = "sqlite:///./classsnap.db"

    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    models_dir: Path = Field(default_factory=lambda: Path("./models"))
    yunet_model_path: Path = Field(default_factory=lambda: Path("./models/face_detection_yunet_2023mar.onnx"))
    sface_model_path: Path = Field(default_factory=lambda: Path("./models/face_recognition_sface_2021dec.onnx"))
    upload_dir: Path = Field(default_factory=lambda: Path("./uploads"))
    exports_dir: Path = Field(default_factory=lambda: Path("./exports"))
    max_upload_size_bytes: int = 10 * 1024 * 1024

    # Computer Vision & Tiled Detection
    tile_size: int = 640
    tile_overlap: float = 0.25
    detection_score_threshold: float = 0.65
    iou_merge_threshold: float = 0.40
    enable_tiled_detection: bool = True
    # Small-face recovery: photos whose longest side is well below this are
    # bicubically upscaled (at most max_detection_upscale x) before detection
    # and alignment, so 12-24 px faces in compressed classroom photos are found
    # and aligned on precise landmarks. min_face_size_px is measured in the
    # original photo.
    small_face_target_side: int = 3840
    max_detection_upscale: float = 3.0
    min_face_size_px: int = 12

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.max_upload_size_bytes <= 0:
            raise ValueError("max_upload_size_bytes must be positive")
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if len(self.secret_key) < 32 or self.secret_key == Settings.model_fields["secret_key"].default:
                raise ValueError("A unique SECRET_KEY of at least 32 characters is required in production")
        return self

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
