"""Per-field confidence carried by any extracted record (modular-plan.md §2.1)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.enums import ConfidenceSource


class Confidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_confidence: dict[str, float] = Field(default_factory=dict)
    overall: float
    source: ConfidenceSource

    def low_fields(self, threshold: float) -> list[str]:
        """Fields at or below the confirmation threshold, never written silently."""
        return [field for field, score in self.field_confidence.items() if score < threshold]
