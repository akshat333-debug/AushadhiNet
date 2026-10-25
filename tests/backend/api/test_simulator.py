"""DoD test for backend/api/simulator.py (step 31): both capture channels
(Twilio and the simulator) funnel through the SAME handler function, proven
by object identity, not by re-running similar assertions against separate
implementations."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.providers import factory


def test_simulator_calls_the_same_function_as_twilio():
    """Call-graph assertion: not "produces the same result" (which two
    independent implementations could coincidentally satisfy) but "is
    the literal same function object"."""
    import backend.api.simulator as simulator_module
    import backend.api.webhooks_twilio as twilio_module

    assert simulator_module.publish_inbound_message is twilio_module.publish_inbound_message


def test_simulator_message_queues_same_payload_shape_as_twilio():
    factory.get.cache_clear()
    client = TestClient(create_app())
    received = []
    factory.get("queue").subscribe("ingest.raw_message", lambda payload: received.append(payload))

    response = client.post("/simulator/message", json={
        "from_phone": "whatsapp:+911234567890", "body": "ORS 50", "message_id": "SIM1",
    })
    assert response.status_code == 200
    assert len(received) == 1
    assert received[0]["body"] == "ORS 50"
    assert received[0]["reporter_phone_hash"]


def test_simulator_media_base64_becomes_data_uri():
    factory.get.cache_clear()
    client = TestClient(create_app())
    received = []
    factory.get("queue").subscribe("ingest.raw_message", lambda payload: received.append(payload))

    import base64
    encoded = base64.b64encode(b"fake-image-bytes").decode()
    client.post("/simulator/message", json={
        "from_phone": "whatsapp:+911234567890", "media_base64": encoded,
        "media_content_type": "image/jpeg", "message_id": "SIM2",
    })
    assert received[0]["media_url"].startswith("data:image/jpeg;base64,")
    assert received[0]["num_media"] == 1


def test_media_messages_are_capped_per_minute(monkeypatch):
    """Each photo or voice note is a paid Gemini/Chirp call and the simulator is public in demo mode."""
    import base64
    from collections import deque
    import backend.api.simulator as sim
    monkeypatch.setattr(sim, "MEDIA_PER_MINUTE", 2)
    monkeypatch.setattr(sim, "_media_times", deque())
    client = TestClient(create_app())
    media = {"from_phone": "whatsapp:+10000000000", "media_base64": base64.b64encode(b"x").decode(), "media_content_type": "image/jpeg"}
    assert [client.post("/simulator/message", json={**media, "message_id": f"m{i}"}).status_code for i in range(3)] == [200, 200, 429]
    assert client.post("/simulator/message", json={"from_phone": "whatsapp:+10000000000", "body": "ORS 5", "message_id": "t"}).status_code == 200
