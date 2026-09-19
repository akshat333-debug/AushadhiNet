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


class LocalMessaging:
    def __init__(self):
        self.sent: list[SentMessage] = []

    def send_text(self, to: str, body: str) -> None:
        self.sent.append(SentMessage(to=to, kind="text", body=body))

    def send_media(self, to: str, url: str) -> None:
        self.sent.append(SentMessage(to=to, kind="media", body=url))

    def send_buttons(self, to: str, body: str, buttons: list[str]) -> None:
        self.sent.append(SentMessage(to=to, kind="buttons", body=body, extra={"buttons": buttons}))
