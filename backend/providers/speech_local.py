"""Local speech provider (modular-plan.md §2.2): replays fixture
transcripts keyed by a hash of the audio bytes, so tests and the demo
work without a real speech API. `backend/providers/fixtures/speech/`
holds `{sha256(audio)[:16]}.json` files with `{"text","language","confidence"}`.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from backend.providers.base import ProviderError, Transcript

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures" / "speech"


class LocalSpeechProvider:
    def transcribe(self, audio: bytes, mime: str, lang_hint: str | None = None) -> Transcript:
        key = hashlib.sha256(audio).hexdigest()[:16]
        fixture_path = FIXTURES_DIR / f"{key}.json"
        if not fixture_path.exists():
            raise ProviderError(
                f"no local speech fixture for audio hash {key}. "
                f"Add {fixture_path} with {{'text','language','confidence'}}, "
                "or switch AUSHADHI_MODE=cloud for a real transcription."
            )
        data = json.loads(fixture_path.read_text())
        return Transcript(text=data["text"], language=data["language"], confidence=data["confidence"])
