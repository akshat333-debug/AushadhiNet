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
    _local_only()  # in cloud mode this would let anyone post reports as any number
    media_url = None
    if msg.media_base64:
        media_url = f"data:{msg.media_content_type or 'application/octet-stream'};base64,{msg.media_base64}"

    publish_inbound_message(
        from_=msg.from_phone, body=msg.body, num_media=1 if media_url else 0,
        media_url=media_url, media_content_type=msg.media_content_type,
        message_sid=msg.message_id,
    )
    return {"status": "queued"}


def _local_only() -> None:
    from fastapi import HTTPException
    from backend.config import get_settings
    if get_settings().mode != "local":
        raise HTTPException(404, "simulator endpoints exist only in local mode")


@router.get("/contacts")
def simulator_contacts(limit: int = 25) -> list[dict]:
    """Pilot-district facilities with their dev WhatsApp numbers, for the simulator's sender picker."""
    _local_only()
    from backend.runtime import PILOT_DISTRICT, phone_for_facility
    from ml.data.facilities import facility_index
    facilities = [f for f in facility_index().values() if f.district_id == PILOT_DISTRICT][:limit]
    return [{"facility_id": f.facility_id, "name": f.name, "phone": phone_for_facility(f.facility_id)} for f in facilities]


@router.get("/outbox")
def simulator_outbox(phone: str) -> list[dict]:
    """Replies the local messaging provider 'sent' to one number (what WhatsApp would deliver)."""
    _local_only()
    from backend.providers import factory
    sent = factory.get("messaging").sent
    return [
        {"seq": i, "kind": m.kind, "body": "[voice note]" if m.kind == "media" else m.body, "buttons": m.extra.get("buttons", [])}
        for i, m in enumerate(sent) if m.to == phone
    ]
