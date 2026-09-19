"""Local text-to-speech provider (modular-plan.md §2.2): returns a
deterministic placeholder audio payload (not real audio) so callers can
exercise the "synthesize and send" path without a Cloud TTS call.
"""
from __future__ import annotations


class LocalTTSProvider:
    def synthesize(self, text: str, lang: str) -> bytes:
        return f"[local-tts:{lang}] {text}".encode("utf-8")
