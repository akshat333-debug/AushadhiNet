"""DoD test for backend/ingest/media.py (step 26)."""
from __future__ import annotations

import pytest

from backend.config import Settings
from backend.ingest.media import validate
from backend.providers.base import ProviderError


def _settings():
    return Settings(_env_file=None)


def test_exe_rejected():
    with pytest.raises(ProviderError):
        validate("application/x-msdownload", 100, b"x" * 100, settings=_settings())


def test_oversized_jpeg_rejected():
    settings = _settings()
    size = (settings.max_upload_mb + 1) * 1024 * 1024
    with pytest.raises(ProviderError):
        validate("image/jpeg", size, b"x" * size, settings=settings)


def test_valid_jpeg_under_cap_accepted():
    settings = _settings()
    data = b"x" * 1000
    validate("image/jpeg", len(data), data, settings=settings)  # must not raise


def test_declared_size_mismatch_rejected():
    with pytest.raises(ProviderError):
        validate("image/jpeg", 100, b"x" * 50, settings=_settings())


def test_valid_audio_accepted():
    settings = _settings()
    data = b"x" * 500
    validate("audio/ogg", len(data), data, settings=settings)
