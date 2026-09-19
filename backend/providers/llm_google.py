"""Gemini provider via the `google-genai` SDK (architecture.md §1). Used
for structured extraction (register photos -> StockRecord/BedCensus/
CheckIn) and for the officer agent's free-form generation.
"""
from __future__ import annotations

from backend.config import get_settings
from backend.providers.base import LLMResponse, Media, ProviderError


class GoogleLLMProvider:
    def __init__(self):
        from google import genai

        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    def extract(self, prompt: str, media: list[Media], schema: type):
        from google.genai import types

        parts = [types.Part.from_bytes(data=m.data, mime_type=m.mime) for m in media]
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[prompt, *parts],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=schema,
                ),
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Gemini extraction failed: {e}") from e

        if response.parsed is None:
            raise ProviderError("Gemini did not return a schema-conformant response")
        # Gemini structured output does not natively return per-field
        # confidence; a fixed prompt convention asks for a sibling
        # "<field>_confidence" object, defaulted to 1.0 when absent.
        confidence = getattr(response, "field_confidence", None) or {
            field: 1.0 for field in schema.model_fields
        }
        return response.parsed, confidence

    def generate(self, prompt: str, tools: list[dict] | None = None) -> LLMResponse:
        try:
            response = self._client.models.generate_content(model=self._model, contents=prompt)
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Gemini generation failed: {e}") from e
        return LLMResponse(text=response.text or "", tool_calls=[])
