"""Pub/Sub queue (architecture.md §1)."""
from __future__ import annotations

import json
from typing import Callable

from backend.config import get_settings
from backend.providers.base import ProviderError


class GooglePubSubQueue:
    def __init__(self):
        from google.cloud import pubsub_v1

        self._project = get_settings().gcp_project
        self._publisher = pubsub_v1.PublisherClient()
        self._subscriber = pubsub_v1.SubscriberClient()

    def publish(self, topic: str, payload: dict) -> None:
        topic_path = self._publisher.topic_path(self._project, topic)
        try:
            self._publisher.publish(topic_path, json.dumps(payload).encode("utf-8"))
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Pub/Sub publish failed: {e}") from e

    def subscribe(self, topic: str, handler: Callable) -> None:
        subscription_path = self._subscriber.subscription_path(self._project, f"{topic}-sub")

        def callback(message):
            handler(json.loads(message.data.decode("utf-8")))
            message.ack()

        self._subscriber.subscribe(subscription_path, callback=callback)
