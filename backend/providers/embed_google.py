"""Vertex AI text-embedding provider (architecture.md §1), used for NLEM
drug-name normalisation via Vector Search.
"""
from __future__ import annotations

import numpy as np

from backend.config import get_settings
from backend.providers.base import ProviderError


class GoogleEmbedProvider:
    def __init__(self):
        from google import genai

        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def embed(self, texts: list[str]) -> np.ndarray:
        try:
            result = self._client.models.embed_content(model="text-embedding-004", contents=texts)
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"embedding request failed: {e}") from e
        return np.array([e.values for e in result.embeddings])
