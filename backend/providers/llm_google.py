"""Gemini provider via the `google-genai` SDK (architecture.md §1). Used
for structured extraction (register photos -> StockRecord/BedCensus/
CheckIn) and for the officer agent's free-form generation.
"""
from __future__ import annotations

from backend.config import get_settings
from backend.providers.base import LLMResponse, Media, ProviderError


_CONFIDENCE_FIELDS = ("on_hand", "received", "dispensed", "batch_no", "expiry")


def _gemini_json_schema(schema: type) -> dict:
    """The Developer API rejects `additionalProperties`, which is how pydantic renders
    `dict[str, float]`; spell the confidence map out as fixed optional fields instead."""
    def walk(node):
        if isinstance(node, dict):
            if "additionalProperties" in node:
                node = {k: v for k, v in node.items() if k != "additionalProperties"}
                node["properties"] = {f: {"type": "number"} for f in _CONFIDENCE_FIELDS}
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node
    return walk(schema.model_json_schema())


class GoogleLLMProvider:
    def __init__(self):
        from google import genai

        settings = get_settings()
        # A hung call would stall a nurse's reply or an officer's answer; the callers fall back.
        self._client = genai.Client(api_key=settings.gemini_api_key, http_options=genai.types.HttpOptions(timeout=45_000))
        self._model = settings.gemini_model

    def extract(self, prompt: str, media: list[Media], schema: type):
        from google.genai import types

        parts = [types.Part.from_bytes(data=m.data, mime_type=m.mime) for m in media]
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[prompt, *parts],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_json_schema=_gemini_json_schema(schema),
                ),
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Gemini extraction failed: {e}") from e

        try:
            parsed = schema.model_validate_json(response.text or "")
        except ValueError as e:
            raise ProviderError("Gemini did not return a schema-conformant response") from e
        # The API returns no per-field confidence; the schema asks Gemini to self-report it inside
        # the JSON (StockExtraction.confidence). Self-reports are uncalibrated, which is why every
        # photo and voice read waits for the nurse's YES. This map is only a floor for callers that
        # read it: absent means unknown, never certain.
        return parsed, {field: 0.0 for field in schema.model_fields}

    def generate(self, prompt: str, tools: list[dict] | None = None, timeout_s: float = 45) -> LLMResponse:
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self._model, contents=prompt,
                config=types.GenerateContentConfig(http_options=types.HttpOptions(timeout=int(max(timeout_s, 10) * 1000))),  # the API rejects deadlines under 10 s
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Gemini generation failed: {e}") from e
        return LLMResponse(text=response.text or "", tool_calls=[])

    def run_tools(self, system: str, question: str, declarations: list[dict], call, max_steps: int = 5, timeout_s: float = 25) -> str:
        """Gemini function calling, run by hand: Gemini picks a declared function, `call` runs it
        (jurisdiction-checked in backend/agent/tools.py) and the result goes back, until Gemini
        answers in text. Only declared functions exist; none of them can approve or send."""
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=[types.FunctionDeclaration(**d) for d in declarations])],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            http_options=types.HttpOptions(timeout=int(max(timeout_s, 10) * 1000)),
        )
        contents = [types.Content(role="user", parts=[types.Part(text=question)])]
        for _ in range(max_steps):
            try:
                response = self._client.models.generate_content(model=self._model, contents=contents, config=config)
            except Exception as e:  # noqa: BLE001
                raise ProviderError(f"Gemini tool call failed: {e}") from e
            calls = response.function_calls or []
            if not calls:
                return (response.text or "").strip()
            contents.append(response.candidates[0].content)
            contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name=fc.name, response={"result": call(fc.name, dict(fc.args or {}))})
                for fc in calls
            ]))
        raise ProviderError("Gemini kept calling tools without answering")
