"""Local messaging provider (modular-plan.md §2.2): appends every send to
an in-memory log instead of calling Twilio, so tests can assert on what
would have been sent (the WhatsApp simulator UI reads this log too).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SentMessage:
    to: str
    kind: str  # "text" | "media" | "buttons"
    body: str
    extra: dict = field(default_factory=dict)


# The cloud demo runs this for days and each approval logs two voice clips, so only the newest
# messages are kept. shortcut: older simulator threads lose their start past this cap.
MAX_SENT = 2000


class LocalMessaging:
    def __init__(self):
        self.sent: list[SentMessage] = []

    def _log(self, message: SentMessage) -> None:
        self.sent.append(message)
        del self.sent[:-MAX_SENT]

    def send_text(self, to: str, body: str) -> None:
        self._log(SentMessage(to=to, kind="text", body=body))

    def send_media(self, to: str, url: str) -> None:
        self._log(SentMessage(to=to, kind="media", body=url))

    def send_buttons(self, to: str, body: str, buttons: list[str]) -> None:
        self._log(SentMessage(to=to, kind="buttons", body=body, extra={"buttons": buttons}))
