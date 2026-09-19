"""Local translation provider (modular-plan.md §2.2): identity passthrough
tagged with the target language, so the pipeline shape (translate -> send)
is exercised without a real Translation API call.
"""
from __future__ import annotations


class LocalTranslateProvider:
    def translate(self, text: str, target_lang: str) -> str:
        return text if target_lang.lower() in ("en", "en-in") else f"[{target_lang}] {text}"
