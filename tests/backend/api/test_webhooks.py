"""DoD test for backend/app.py + api/webhooks_twilio.py (step 29)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.providers import factory


def _client():
    factory.get.cache_clear()
    return TestClient(create_app())


def test_webhook_returns_200_immediately():
    client = _client()
    response = client.post("/webhooks/twilio", data={"From": "whatsapp:+911234567890", "Body": "ORS 50", "NumMedia": "0", "MessageSid": "SM1"})
    assert response.status_code == 200


def test_webhook_queues_the_raw_message():
    factory.get.cache_clear()
    from backend.config import Settings
    import backend.providers.factory as factory_module
    monkey_settings = Settings(_env_file=None)
    factory_module.get_settings = lambda: monkey_settings  # local mode

    from backend.app import create_app as _create_app
    app = _create_app()
    client = TestClient(app)

    received = []
    factory.get("queue").subscribe("ingest.raw_message", lambda payload: received.append(payload))

    client.post("/webhooks/twilio", data={"From": "whatsapp:+911234567890", "Body": "ORS 50", "NumMedia": "0", "MessageSid": "SM2"})
    assert len(received) == 1
    assert received[0]["body"] == "ORS 50"
    assert received[0]["reporter_phone_hash"]  # phone number is hashed, not stored raw


def test_webhook_hashes_phone_never_stores_raw_number():
    factory.get.cache_clear()
    from backend.app import create_app as _create_app
    client = TestClient(_create_app())
    received = []
    factory.get("queue").subscribe("ingest.raw_message", lambda payload: received.append(payload))
    client.post("/webhooks/twilio", data={"From": "whatsapp:+919999999999", "Body": "x", "NumMedia": "0", "MessageSid": "SM3"})
    assert "+919999999999" not in str(received[0]["reporter_phone_hash"])


def test_local_mode_skips_signature_validation():
    """No real Twilio secret exists locally; the webhook must not 403 a
    plain local-mode POST for lacking a signature."""
    client = _client()
    response = client.post("/webhooks/twilio", data={"From": "whatsapp:+911234567890", "NumMedia": "0", "MessageSid": "SM4"})
    assert response.status_code == 200


def test_cloud_mode_unsigned_request_is_rejected(monkeypatch):
    from backend.config import Settings
    import backend.api.webhooks_twilio as webhook_module

    cloud_settings = Settings(_env_file=None)
    cloud_settings.mode = "cloud"
    cloud_settings.twilio_auth_token = "test-auth-token"
    monkeypatch.setattr(webhook_module, "get_settings", lambda: cloud_settings)

    client = _client()
    response = client.post("/webhooks/twilio", data={"From": "whatsapp:+911234567890", "Body": "x", "NumMedia": "0", "MessageSid": "SM5"})
    assert response.status_code == 403


def test_cloud_mode_correctly_signed_request_is_accepted(monkeypatch):
    from twilio.request_validator import RequestValidator

    from backend.config import Settings
    import backend.api.webhooks_twilio as webhook_module

    cloud_settings = Settings(_env_file=None)
    cloud_settings.mode = "cloud"
    cloud_settings.twilio_auth_token = "test-auth-token"
    monkeypatch.setattr(webhook_module, "get_settings", lambda: cloud_settings)

    client = _client()
    url = "http://testserver/webhooks/twilio"
    form = {"From": "whatsapp:+911234567890", "Body": "x", "NumMedia": "0", "MessageSid": "SM6"}
    validator = RequestValidator("test-auth-token")
    signature = validator.compute_signature(url, form)

    response = client.post("/webhooks/twilio", data=form, headers={"X-Twilio-Signature": signature})
    assert response.status_code == 200
