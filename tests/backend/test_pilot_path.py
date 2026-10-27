"""What a real (non-simulator) rollout needs: voice alerts Twilio can fetch, alerts only to
registered numbers, numbered replies, and two concurrent proposals leaving one plan."""
from __future__ import annotations

import threading

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.providers import factory


def test_voice_alert_is_a_fetchable_url_when_messaging_is_real(monkeypatch):
    from backend.action import alerts
    from backend.config import get_settings
    monkeypatch.setattr(get_settings(), "public_api_url", "https://api.example")
    monkeypatch.setattr(factory, "get", (lambda real: lambda name: object() if name == "messaging" else real(name))(factory.get))
    with TestClient(create_app()) as client:
        url = alerts.voice_url(b"OggS-voice")
        assert url.startswith("https://api.example/public/voice/") and url.endswith(".ogg")
        assert client.get(url.removeprefix("https://api.example")).content == b"OggS-voice"
        assert client.get("/public/voice/nothere.ogg").status_code == 404


def test_without_demo_mode_only_registered_numbers_get_alerts(monkeypatch):
    from backend.config import get_settings
    from backend.providers.store_live_local import LocalLiveStore
    from backend.runtime import contact_phone
    store = LocalLiveStore()
    monkeypatch.setattr(factory, "get", lambda name: store)
    settings = get_settings()
    monkeypatch.setattr(settings, "mode", "cloud")
    monkeypatch.setattr(settings, "demo_mode", False)
    assert contact_phone("MH-0000221") is None


def test_numbered_reply_confirms_like_yes():
    from tests.backend.test_flow_integrity import PHONE, _send
    with TestClient(create_app()) as client:
        _send(client, body="Zync 40")
        assert _send(client, phone=PHONE, body="1")[-1] == "Confirmed 1 record(s)."


def test_two_proposals_at_once_leave_one_active_plan():
    from backend.domain import OrderStatus
    from backend.runtime import propose_for_district, replace_drafts
    with TestClient(create_app()):
        drafts = [propose_for_district("mh/nashik") for _ in range(2)]
        threads = [threading.Thread(target=replace_drafts, args=("mh/nashik", d)) for d in drafts]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        active = {o.order_id for o in factory.get("store_live").query("orders", {"status": OrderStatus.DRAFT})}
        assert active in ({o.order_id for o in drafts[0]}, {o.order_id for o in drafts[1]})


def test_a_clip_over_the_store_limit_is_not_stored(monkeypatch):
    from backend.action import alerts
    from backend.config import get_settings
    monkeypatch.setattr(get_settings(), "public_api_url", "https://api.example")
    monkeypatch.setattr(factory, "get", (lambda real: lambda name: object() if name == "messaging" else real(name))(factory.get))
    assert alerts.voice_url(b"x" * 700_000) is None
