import json

from backend.ingest.schemas import StockExtraction
from backend.providers.llm_google import _gemini_json_schema


def test_schema_has_no_additional_properties():
    # The Gemini Developer API rejects additionalProperties (how pydantic renders dict fields).
    schema = _gemini_json_schema(StockExtraction)
    assert "additionalProperties" not in json.dumps(schema)
    assert "on_hand" in schema["properties"]["confidence"]["properties"]
