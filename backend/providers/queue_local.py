"""Local queue (modular-plan.md §2.2): synchronous in-process pub/sub,
standing in for Pub/Sub. `publish` calls subscribed handlers immediately
and synchronously -- fine for tests and a single-process demo; a real
queue is what makes this durable and async across processes.
"""
from __future__ import annotations

from typing import Callable


class LocalQueue:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def publish(self, topic: str, payload: dict) -> None:
        for handler in self._subscribers.get(topic, []):
            handler(payload)

    def subscribe(self, topic: str, handler: Callable) -> None:
        self._subscribers.setdefault(topic, []).append(handler)
