"""Web WhatsApp simulator endpoint (project.md's Twilio-sandbox-plus-
simulator decision): the frontend's chat UI posts here directly, with
media as base64 rather than a Twilio media URL. Funnels through the exact
same `publish_inbound_message` as the real Twilio webhook -- proven by
identity in tests/backend/api/test_simulator.py, not by copy-pasting the
handler.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.api.webhooks_twilio import publish_inbound_message

router = APIRouter(prefix="/simulator", tags=["simulator"])


class SimulatorMessage(BaseModel):
    from_phone: str
    body: str | None = None
    media_base64: str | None = None
    media_content_type: str | None = None
    message_id: str


@router.post("/message")
async def simulator_message(msg: SimulatorMessage) -> dict:
    media_url = None
    if msg.media_base64:
        media_url = f"data:{msg.media_content_type or 'application/octet-stream'};base64,{msg.media_base64}"

    publish_inbound_message(
        from_=msg.from_phone, body=msg.body, num_media=1 if media_url else 0,
        media_url=media_url, media_content_type=msg.media_content_type,
        message_sid=msg.message_id,
    )
    return {"status": "queued"}
