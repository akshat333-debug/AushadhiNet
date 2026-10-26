"""The operational flow under the cases a mock judge probed: odd quantities, two pending cards,
redelivered messages, approving stock that is no longer there, alerts that fail, receipt."""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.domain import BatchLine, OrderKind, OrderStatus, RecordStatus, TransferOrder
from backend.providers import factory
from backend.runtime import latest_records, phone_for_facility

OFFICER = {"Authorization": "Bearer dev:o1:district:mh/nashik"}
SRC, DST = "MH-0000221", "MH-0000223"
PHONE = phone_for_facility(SRC)


def _send(client, phone=PHONE, mid=None, **message):
    client.post("/simulator/message", json={"from_phone": phone, "message_id": mid or uuid.uuid4().hex, **message})
    return [m["body"] for m in client.get("/simulator/outbox", params={"phone": phone}).json()]


@pytest.mark.parametrize("body, on_hand", [("ORS 1,000", 1000), ("ORS 1,00,000", 100000), ("ORS-7", 7)])
def test_grouped_numbers_are_read_whole(body, on_hand):
    with TestClient(create_app()) as client:
        _send(client, body=body)
        assert latest_records()[(SRC, "ors")].on_hand == on_hand


@pytest.mark.parametrize("body", ["ORS -5", "ORS 10.5"])
def test_negative_or_decimal_quantity_is_refused_not_guessed(body):
    with TestClient(create_app()) as client:
        before = latest_records()[(SRC, "ors")].on_hand
        replies = _send(client, body=body)
        assert replies[-1].startswith(f"Not recorded: {body}.")
        assert latest_records()[(SRC, "ors")].on_hand == before


def test_yes_confirms_only_the_latest_card():
    """Regression: YES used to confirm every pending report of the facility, including an older, wrong read."""
    from backend.providers.speech_local import FIXTURES_DIR
    import hashlib
    import json
    with TestClient(create_app()) as client:
        for n, text in ((1, "ORS 5"), (2, "ORS 50")):
            audio = b"OggS" + f"voice-{n}-{uuid.uuid4().hex}".encode()
            FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
            fixture = FIXTURES_DIR / f"{hashlib.sha256(audio).hexdigest()[:16]}.json"
            fixture.write_text(json.dumps({"text": text, "language": "en-IN", "confidence": 0.9}))
            try:
                _send(client, media_base64=base64.b64encode(audio).decode(), media_content_type="audio/ogg")
            finally:
                fixture.unlink()
        assert _send(client, body="YES")[-1] == "Confirmed 1 record(s)."
        assert latest_records()[(SRC, "ors")].on_hand == 50
        rejected = factory.get("store_live").query("stock_records", {"facility_id": SRC, "status": RecordStatus.REJECTED})
        assert [r.on_hand for r in rejected] == [5]


def test_redelivered_message_is_handled_once():
    with TestClient(create_app()) as client:
        _send(client, mid="SM-dup", body="ORS 77")
        replies = _send(client, mid="SM-dup", body="ORS 77")
        assert sum("ORS 77" in r for r in replies) == 1
        assert sum(r.on_hand == 77 for r in factory.get("store_live").query("stock_records", {"facility_id": SRC})) == 1


def test_renamed_executable_never_reaches_the_photo_reader():
    with TestClient(create_app()) as client:
        replies = _send(client, media_base64=base64.b64encode(b"MZ" + b"x" * 200).decode(), media_content_type="image/jpeg")
        assert replies[-1].startswith("Could not read that.")


def _order(order_id: str, quantity: int) -> None:
    factory.get("store_live").put("orders", order_id, TransferOrder(
        order_id=order_id, kind=OrderKind.DRUG_TRANSFER, from_facility_id=SRC, to_facility_id=DST, drug_id="ors",
        quantity=quantity, batches=[BatchLine(batch_no="B1", quantity=quantity)], drive_minutes=10.0,
        rationale="test", created_at=datetime.now(timezone.utc), created_by="solver"))


def test_the_same_units_cannot_be_approved_twice():
    with TestClient(create_app()) as client:
        _send(client, body="ORS 60")
        _order("o-a", 50)
        _order("o-b", 50)
        assert client.post("/officer/orders/o-a/approve", headers=OFFICER).status_code == 200
        response = client.post("/officer/orders/o-b/approve", headers=OFFICER)
        assert response.status_code == 409 and "has 10 units" in response.json()["detail"]
        from backend.runtime import projected_stock
        assert projected_stock({SRC, DST})[(SRC, "ors")] == 10  # what the next proposal sees
        _send(client, body="ORS 10")  # the nurse's next report already reflects the transfer
        assert projected_stock({SRC})[(SRC, "ors")] == 10


def test_failed_alerts_leave_the_order_approved_and_retry_resends(monkeypatch):
    import backend.api.officer as officer
    with TestClient(create_app()) as client:
        _send(client, body="ORS 60")
        _order("o-c", 20)
        real = officer.send_transfer_alerts
        monkeypatch.setattr(officer, "send_transfer_alerts", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("WhatsApp down")))
        assert client.post("/officer/orders/o-c/approve", headers=OFFICER).status_code == 502
        stored = factory.get("store_live").get("orders", "o-c")
        assert stored.status == OrderStatus.APPROVED and stored.alerted_at is None
        monkeypatch.setattr(officer, "send_transfer_alerts", real)
        retried = client.post("/officer/orders/o-c/approve", headers=OFFICER).json()
        assert retried["alerted_at"] is not None and retried["signature"] == stored.signature


def test_destination_confirms_receipt_on_whatsapp():
    with TestClient(create_app()) as client:
        _send(client, body="ORS 60")
        _order("abcdef12-order", 20)
        assert client.post("/officer/orders/abcdef12-order/approve", headers=OFFICER).status_code == 200
        dst_phone = phone_for_facility(DST)
        assert _send(client, phone=dst_phone, body="RECEIVED 00000000")[-1].startswith("No transfer 00000000")
        assert _send(client, phone=dst_phone, body="received abcdef12")[-1] == "Receipt recorded for transfer abcdef12. Thank you."
        assert factory.get("store_live").get("orders", "abcdef12-order").status == OrderStatus.RECEIVED


@pytest.mark.parametrize("reply, kept", [("Yes.", 1), ("hello", None)])
def test_casual_reply_never_discards_the_pending_card(reply, kept):
    with TestClient(create_app()) as client:
        _send(client, body="Zync 40")  # fuzzy drug name: waits for YES
        pending = factory.get("store_live").query("stock_records", {"facility_id": SRC, "status": RecordStatus.PENDING})
        assert pending
        _send(client, body=reply)
        if kept:
            _send(client, body="YES")  # harmless if "Yes." already confirmed it
            assert factory.get("store_live").get("stock_records", pending[0].record_id).status == RecordStatus.CONFIRMED
        else:
            assert factory.get("store_live").get("stock_records", pending[0].record_id).status == RecordStatus.PENDING


def test_voice_note_numbers_survive_the_outbox_cap(monkeypatch):
    from backend.providers import messaging_local
    monkeypatch.setattr(messaging_local, "MAX_SENT", 3)
    m = messaging_local.LocalMessaging()
    for i in range(5):
        m.send_text("p", f"t{i}")
    assert [s.seq for s in m.sent] == [2, 3, 4]
