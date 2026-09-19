"""Local LLM provider (modular-plan.md §2.2): replays fixture extraction
results keyed by a hash of (prompt, media, schema name), and returns a
canned tool-free response for `generate()`. Lets the whole capture ->
extraction -> confirmation loop run and be tested without a Gemini key.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from backend.providers.base import LLMResponse, Media, ProviderError

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures" / "llm"


class LocalLLMProvider:
    def extract(self, prompt: str, media: list[Media], schema: type):
        media_hash = hashlib.sha256(b"".join(m.data for m in media)).hexdigest()[:16]
        key = hashlib.sha256(f"{prompt}|{media_hash}|{schema.__name__}".encode()).hexdigest()[:16]
        fixture_path = FIXTURES_DIR / f"{key}.json"
        if not fixture_path.exists():
            raise ProviderError(
                f"no local LLM extraction fixture for key {key} (schema {schema.__name__}). "
                f"Add {fixture_path} with {{'fields': {{...}}, 'confidence': {{...}}}}, "
                "or switch AUSHADHI_MODE=cloud for a real Gemini call."
            )
        data = json.loads(fixture_path.read_text())
        instance = schema.model_validate(data["fields"])
        return instance, data["confidence"]

    def generate(self, prompt: str, tools: list[dict] | None = None) -> LLMResponse:
        return LLMResponse(text=f"[local-llm stub response to: {prompt[:60]}...]", tool_calls=[])
