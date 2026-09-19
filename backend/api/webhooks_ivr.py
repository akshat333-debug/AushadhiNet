"""IVR capture via Dialogflow CX telephony (project.md FR1, architecture.md
§1). Dialogflow CX posts a webhook fulfillment request carrying the
caller's number and the recognized speech text; this is converted to the
same raw-message shape and funnelled through `publish_inbound_message`,
same as WhatsApp and the simulator (modular-plan.md step 31).
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from backend.api.webhooks_twilio import publish_inbound_message

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/ivr")
async def ivr_webhook(request: Request) -> dict:
    body = await request.json()
    # Dialogflow CX webhook fulfillment shape: sessionInfo.parameters
    # carries slot-filled values; we use the raw transcript of the
    # caller's utterance as the message body, same as a voice note's
    # transcript would be, and let the same extraction pipeline handle it.
    session_info = body.get("sessionInfo", {}) or {}
    params = session_info.get("parameters", {}) or {}
    caller_number = params.get("caller_id", "unknown")
    transcript = body.get("text") or params.get("last_utterance", "")

    publish_inbound_message(
        from_=f"ivr:{caller_number}", body=transcript, num_media=0,
        media_url=None, media_content_type=None,
        message_sid=body.get("responseId", ""),
    )
    return {"fulfillmentResponse": {"messages": [{"text": {"text": ["Thank you, your report has been recorded."]}}]}}
