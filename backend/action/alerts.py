"""Local-language WhatsApp + voice alerts for an approved order (modular-
plan.md §5.5, AC8): the source and destination facility in-charges each
get a text alert and a spoken version in their own language, plus the
route plan.
"""
from __future__ import annotations

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
        # in cloud mode this would upload `audio` and send the media URL;
        # local mode logs the media payload directly for the demo/tests
        messaging.send_media(phone, f"data:audio/ogg;base64,{_b64(audio)}")


def _b64(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode("ascii")


def route_plan_text(order: TransferOrder, from_facility: Facility, to_facility: Facility) -> str:
    route_provider = factory.get("routes")
    minutes = route_provider.drive_minutes(from_facility, to_facility)
    return f"Route: {from_facility.name} -> {to_facility.name}, approx {minutes:.0f} min drive."
