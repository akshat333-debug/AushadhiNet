"""Validates uploaded media before anything touches a provider (modular-
plan.md §2.4): MIME allow-list and size cap, both from config, and the file's own
signature, so a renamed executable never reaches Gemini or Chirp.
"""
from __future__ import annotations

from backend.config import Settings
from backend.providers.base import ProviderError


# First bytes of each allowed format (mp4 carries "ftyp" at offset 4, checked separately).
_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG",), "image/webp": (b"RIFF",),
    "audio/ogg": (b"OggS",), "audio/amr": (b"#!AMR",), "audio/mpeg": (b"ID3", b"\xff"), "audio/webm": (b"\x1aE\xdf\xa3",),
}


def validate(content_type: str, size: int, data: bytes, settings: Settings | None = None) -> None:
    from backend.config import get_settings

    settings = settings or get_settings()
    content_type = content_type.split(";")[0].strip()  # "audio/ogg; codecs=opus"
    if content_type not in settings.allowed_mime_set:
        raise ProviderError(f"rejected upload: MIME type '{content_type}' is not in the allow-list")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size > max_bytes:
        raise ProviderError(f"rejected upload: {size} bytes exceeds the {settings.max_upload_mb} MB cap")
    if len(data) != size:
        raise ProviderError("rejected upload: declared size does not match actual payload size")
    if content_type == "audio/mp4" and data[4:8] != b"ftyp" or not data.startswith(_SIGNATURES.get(content_type, (b"",))):
        raise ProviderError(f"rejected upload: content is not a real {content_type} file")
