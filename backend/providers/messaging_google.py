"""Twilio WhatsApp sandbox messaging (architecture.md §1, project.md's
"Twilio sandbox + web simulator" decision -- swappable to the Meta Cloud
API later by adding a `messaging_meta.py` behind the same protocol)."""
from __future__ import annotations

from backend.config import get_settings
from backend.providers.base import ProviderError


class TwilioMessaging:
    def __init__(self):
        from twilio.rest import Client

        settings = get_settings()
        self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self._from = settings.twilio_whatsapp_from

    def send_text(self, to: str, body: str) -> None:
        self._send(to, body=body)

    def send_media(self, to: str, url: str) -> None:
        self._send(to, body=None, media_url=[url])

    def send_buttons(self, to: str, body: str, buttons: list[str]) -> None:
        # Twilio WhatsApp quick-reply buttons require a pre-approved
        # content template; falls back to a numbered plain-text list,
        # which the officer/ANM answers by replying with the number.
        numbered = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(buttons))
        self._send(to, body=f"{body}\n{numbered}")

    def _send(self, to: str, body: str | None, media_url: list[str] | None = None) -> None:
        try:
            self._client.messages.create(
                to=f"whatsapp:{to}" if not to.startswith("whatsapp:") else to,
                from_=self._from, body=body, media_url=media_url,
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Twilio send failed: {e}") from e
