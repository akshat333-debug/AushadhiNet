"""Twilio WhatsApp sandbox webhook (modular-plan.md §2.3/§2.4): validates
the request signature in cloud mode, then queues the raw message for the
worker (backend/api/worker.py) rather than doing extraction inline -- the
webhook must return fast (architecture.md §4 step 1: "200 returned
immediately, message queued").

`publish_inbound_message` is the one shared entry point every capture
channel (Twilio, the web simulator, IVR) funnels through, so they are
provably the same pipeline, not three parallel reimplementations
(modular-plan.md step 31's "same handler path... not duplication").
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Request, Response

from backend.config import get_settings
from backend.providers import factory

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _phone_hash(raw_from: str) -> str:
    return hashlib.sha256(raw_from.encode("utf-8")).hexdigest()[:16]


def publish_inbound_message(
    from_: str, body: str | None, num_media: int, media_url: str | None,
    media_content_type: str | None, message_sid: str,
) -> None:
    """The single queue-publish call every inbound channel uses."""
    payload = {
        "from": from_,
        "reporter_phone_hash": _phone_hash(from_),
        "body": body,
        "num_media": num_media,
        "media_url": media_url,
        "media_content_type": media_content_type,
        "message_sid": message_sid,
    }
    factory.get("queue").publish("ingest.raw_message", payload)


def _validate_signature(request: Request, form: dict) -> None:
    settings = get_settings()
    if settings.mode != "cloud":
        return  # no real Twilio secret to validate against in local/demo mode
    from twilio.request_validator import RequestValidator

    signature = request.headers.get("X-Twilio-Signature", "")
    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(str(request.url), form, signature):
        raise HTTPException(status_code=403, detail="invalid Twilio signature")


@router.post("/twilio")
async def twilio_webhook(request: Request) -> Response:
    form = dict(await request.form())
    _validate_signature(request, form)

    publish_inbound_message(
        from_=form.get("From", ""), body=form.get("Body"),
        num_media=int(form.get("NumMedia", "0") or "0"),
        media_url=form.get("MediaUrl0"), media_content_type=form.get("MediaContentType0"),
        message_sid=form.get("MessageSid", ""),
    )

    # Empty TwiML response: we reply asynchronously (alerts/confirmation
    # cards), not inline in the webhook response.
    return Response(content="<Response></Response>", media_type="application/xml", status_code=200)
