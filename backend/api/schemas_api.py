"""API-layer request/response models (modular-plan.md §2.3): distinct from
backend/domain/ -- these describe HTTP shapes (a Twilio webhook payload),
not the underlying data model.
"""
from __future__ import annotations

from pydantic import BaseModel


class TwilioInboundMessage(BaseModel):
    from_: str
    body: str | None = None
    num_media: int = 0
    media_url: str | None = None
    media_content_type: str | None = None
    message_sid: str


class ErrorResponse(BaseModel):
    detail: str
