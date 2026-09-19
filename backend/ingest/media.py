"""Validates uploaded media before anything touches a provider (modular-
plan.md §2.4): MIME allow-list and size cap, both from config.
"""
from __future__ import annotations

from backend.config import Settings
from backend.providers.base import ProviderError


def validate(content_type: str, size: int, data: bytes, settings: Settings | None = None) -> None:
    from backend.config import get_settings

    settings = settings or get_settings()
    if content_type not in settings.allowed_mime_set:
        raise ProviderError(f"rejected upload: MIME type '{content_type}' is not in the allow-list")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size > max_bytes:
        raise ProviderError(f"rejected upload: {size} bytes exceeds the {settings.max_upload_mb} MB cap")
    if len(data) != size:
        raise ProviderError("rejected upload: declared size does not match actual payload size")
