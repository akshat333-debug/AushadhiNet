"""Local-language WhatsApp + voice alerts for an approved order (modular-
plan.md §5.5, AC8): the source and destination facility in-charges each
get a text alert and a spoken version in their own language, plus the
route plan.
"""
from __future__ import annotations

from pydantic import BaseModel

from backend.domain import Facility, TransferOrder
from backend.providers import factory

from backend.action.render_order import render


def send_transfer_alerts(
    order: TransferOrder,
    from_facility: Facility,
    to_facility: Facility,
    from_phone: str,
    to_phone: str,
    lang: str | None = None,
    drug_name: str | None = None,
) -> None:
    """Sends the manifest as text to both ends, plus a voice version, each in
    that recipient's own language (their contact's setting unless `lang` is
    given). AC8: alerts delivered in the recipient's language."""
    from backend.runtime import reply_lang
    messaging = factory.get("messaging")
    translate = factory.get("translate")
    tts = factory.get("tts")

    manifest_en = render(order, from_facility, to_facility, drug_name)

    for phone in (from_phone, to_phone):
        phone_lang = lang or reply_lang({"from": phone})
        manifest_local = manifest_en if phone_lang == "en" else translate.translate(manifest_en, phone_lang)
        messaging.send_text(phone, manifest_local)
        audio = tts.synthesize(manifest_local, phone_lang)
        url = voice_url(audio)
        if url:  # a clip too large to store goes out as text only
            messaging.send_media(phone, url)


class VoiceClip(BaseModel):
    audio_b64: str


# shortcut: clips live in Firestore (1 MiB per document, no expiry); an order alert is well under
# this cap. Move them to a Cloud Storage bucket with a lifecycle rule before alerts run at volume.
MAX_CLIP_B64 = 900_000


def voice_url(audio: bytes) -> str | None:
    """Twilio fetches media from a public URL, so the clip is stored and served by this API at
    an unguessable address (backend/api/public.py). The simulator takes it inline instead."""
    import base64
    import uuid
    from backend.config import get_settings
    from backend.providers.messaging_local import LocalMessaging
    encoded = base64.b64encode(audio).decode("ascii")
    base = get_settings().public_api_url
    if isinstance(factory.get("messaging"), LocalMessaging) or "REPLACE_ME" in base:
        return f"data:audio/ogg;base64,{encoded}"
    if len(encoded) > MAX_CLIP_B64:
        return None
    token = uuid.uuid4().hex
    factory.get("store_live").put("voice_clips", token, VoiceClip(audio_b64=encoded))
    return f"{base.rstrip('/')}/public/voice/{token}.ogg"


def route_plan_text(order: TransferOrder, from_facility: Facility, to_facility: Facility) -> str:
    route_provider = factory.get("routes")
    minutes = route_provider.drive_minutes(from_facility, to_facility)
    return f"Route: {from_facility.name} -> {to_facility.name}, approx {minutes:.0f} min drive."
