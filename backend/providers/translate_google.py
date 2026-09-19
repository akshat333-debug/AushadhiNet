"""Cloud Translation v3 provider (architecture.md §1)."""
from __future__ import annotations

from backend.config import get_settings
from backend.providers.base import ProviderError


class GoogleTranslateProvider:
    def __init__(self):
        from google.cloud import translate

        self._client = translate.TranslationServiceClient()
        self._parent = f"projects/{get_settings().gcp_project}/locations/global"

    def translate(self, text: str, target_lang: str) -> str:
        try:
            response = self._client.translate_text(
                request={"parent": self._parent, "contents": [text],
                         "target_language_code": target_lang, "mime_type": "text/plain"}
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"translation failed: {e}") from e
        return response.translations[0].translated_text
