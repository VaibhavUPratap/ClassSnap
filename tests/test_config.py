"""
Unit tests for ClassSnap centralized configuration.
"""

from pathlib import Path
from classsnap.config import Settings, get_settings
import pytest


def test_default_config_values():
    settings = Settings()
    assert settings.app_name == "ClassSnap"
    assert settings.app_version == "0.1.0"
    assert settings.port == 8000
    assert settings.host == "127.0.0.1"
    assert settings.photo_retention_days == 0
    assert settings.auto_delete_temp_photos is True
    assert isinstance(settings.models_dir, Path)
    assert isinstance(settings.upload_dir, Path)
    assert isinstance(settings.exports_dir, Path)


def test_cached_settings_returns_same_instance():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_environment_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "ClassSnap-TestInstance")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("DEBUG", "true")

    custom_settings = Settings()
    assert custom_settings.app_name == "ClassSnap-TestInstance"
    assert custom_settings.port == 9090
    assert custom_settings.debug is True


def test_production_rejects_insecure_defaults():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            app_env="production",
            debug=False,
            secret_key="dev-secret-key-change-in-production-classsnap-2026",
        )

    with pytest.raises(ValueError, match="DEBUG"):
        Settings(
            app_env="production",
            debug=True,
            secret_key="a-secure-production-secret-key-123456",
        )
