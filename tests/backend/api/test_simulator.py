"""DoD test for backend/api/simulator.py + webhooks_ivr.py (step 31): all
three capture channels funnel through the SAME handler function, proven
by object identity, not by re-running similar assertions against separate
implementations."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.providers import factory


def test_simulator_and_ivr_call_the_same_function_as_twilio():
    """Call-graph assertion: not "produces the same result" (which two
    independent implementations could coincidentally satisfy) but "is
    the literal same function object"."""
    import backend.api.simulator as simulator_module
    import backend.api.webhooks_ivr as ivr_module
    import backend.api.webhooks_twilio as twilio_module

    assert simulator_module.publish_inbound_message is twilio_module.publish_inbound_message
    assert ivr_module.publish_inbound_message is twilio_module.publish_inbound_message


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


def test_ivr_webhook_queues_transcript_as_body():
    factory.get.cache_clear()
    client = TestClient(create_app())
    received = []
    factory.get("queue").subscribe("ingest.raw_message", lambda payload: received.append(payload))

    response = client.post("/webhooks/ivr", json={
        "text": "ORS panas", "sessionInfo": {"parameters": {"caller_id": "+911111111111"}}, "responseId": "R1",
    })
    assert response.status_code == 200
    assert received[0]["body"] == "ORS panas"
    assert received[0]["from"] == "ivr:+911111111111"
