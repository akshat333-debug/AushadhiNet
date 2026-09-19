"""Cloud-mode paths with Google calls faked: push-endpoint verification,
BigQuery table naming, Firebase error handling, simulator lockout."""
from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app

SA = "pubsub-push@proj.iam.gserviceaccount.com"


@pytest.fixture
def cloud(monkeypatch):
    monkeypatch.setenv("AUSHADHI_MODE", "cloud")
    monkeypatch.setenv("PUBSUB_PUSH_AUDIENCE", "https://api.example/internal/pubsub/ingest")
    monkeypatch.setenv("PUBSUB_PUSH_SERVICE_ACCOUNT", SA)
    return TestClient(create_app())


def _envelope(payload: dict) -> dict:
    return {"message": {"data": base64.b64encode(json.dumps(payload).encode()).decode()}}


def _fake_verify(claims=None, error=None):
    def verify(token, request, audience):
        if error:
            raise error
        return claims
    return verify


def test_push_endpoint_is_absent_in_local_mode():
    assert TestClient(create_app()).post("/internal/pubsub/ingest", json={}).status_code == 404


def test_push_refuses_when_unconfigured(monkeypatch):
    monkeypatch.setenv("AUSHADHI_MODE", "cloud")
    assert TestClient(create_app()).post("/internal/pubsub/ingest", json={}, headers={"Authorization": "Bearer x"}).status_code == 503


def test_push_rejects_missing_invalid_and_foreign_tokens(cloud, monkeypatch):
    from google.oauth2 import id_token
    assert cloud.post("/internal/pubsub/ingest", json=_envelope({})).status_code == 401
    monkeypatch.setattr(id_token, "verify_oauth2_token", _fake_verify(error=ValueError("bad signature")))
    assert cloud.post("/internal/pubsub/ingest", json=_envelope({}), headers={"Authorization": "Bearer x"}).status_code == 401
    monkeypatch.setattr(id_token, "verify_oauth2_token", _fake_verify({"email": "attacker@evil.com", "email_verified": True}))
    assert cloud.post("/internal/pubsub/ingest", json=_envelope({}), headers={"Authorization": "Bearer x"}).status_code == 403


def test_verified_push_is_handled_and_malformed_push_is_acked(cloud, monkeypatch):
    from google.oauth2 import id_token
    import backend.runtime as runtime
    handled = []
    monkeypatch.setattr(id_token, "verify_oauth2_token", _fake_verify({"email": SA, "email_verified": True}))
    monkeypatch.setattr(runtime, "handle_inbound", handled.append)
    headers = {"Authorization": "Bearer x"}
    assert cloud.post("/internal/pubsub/ingest", json=_envelope({"from": "whatsapp:+1", "body": "ORS 5"}), headers=headers).status_code == 204
    assert handled == [{"from": "whatsapp:+1", "body": "ORS 5"}]
    assert cloud.post("/internal/pubsub/ingest", json={"nope": 1}, headers=headers).status_code == 204
    assert len(handled) == 1


def test_simulator_is_disabled_in_cloud_mode(cloud):
    response = cloud.post("/simulator/message", json={"from_phone": "whatsapp:+1", "body": "ORS 5", "message_id": "m"})
    assert response.status_code == 404


def test_invalid_firebase_token_is_401_not_500(cloud, monkeypatch):
    from firebase_admin import auth as fb_auth
    import firebase_admin
    monkeypatch.setattr(firebase_admin, "_apps", {"[DEFAULT]": object()})
    monkeypatch.setattr(fb_auth, "verify_id_token", lambda token: (_ for _ in ()).throw(ValueError("malformed")))
    assert cloud.get("/officer/orders/mh/nashik", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_bigquery_inserts_use_qualified_table_and_json_for_nested(monkeypatch):
    monkeypatch.setenv("BIGQUERY_PROJECT", "proj")
    monkeypatch.setenv("BIGQUERY_DATASET", "aushadhinet_mh")
    calls = []

    class FakeClient:
        def __init__(self, project):
            pass

        def insert_rows_json(self, table, rows):
            calls.append((table, rows))
            return []

    from google.cloud import bigquery
    monkeypatch.setattr(bigquery, "Client", FakeClient)
    from backend.providers.store_history_google import GoogleHistoryStore
    GoogleHistoryStore().insert("stock_records", [{"record_id": "r", "confidence": {"overall": 1.0}}])
    assert calls == [("proj.aushadhinet_mh.stock_records", [{"record_id": "r", "confidence": '{"overall": 1.0}'}])]


def test_firestore_store_returns_models_like_the_local_store(monkeypatch):
    """Regression: Firestore returned dicts, so every attribute read (order.status, ...) broke in cloud mode."""
    from datetime import datetime, timezone
    from backend.domain import BatchLine, OrderKind, OrderStatus, TransferOrder
    docs = {}

    class Snap:
        def __init__(self, data):
            self._data, self.exists = data, data is not None

        def to_dict(self):
            return self._data

    class Doc:
        def __init__(self, key):
            self.key = key

        def set(self, data):
            docs[self.key] = data

        def get(self):
            return Snap(docs.get(self.key))

    class Query:
        def __init__(self, col, filters=()):
            self.col, self.filters = col, filters

        def where(self, field, op, value):
            assert not hasattr(value, "value"), "enum passed to Firestore instead of its string"
            return Query(self.col, (*self.filters, (field, value)))

        def document(self, doc_id):
            return Doc((self.col, doc_id))

        def stream(self):
            return [Snap(d) for (c, _), d in docs.items() if c == self.col and all(d.get(f) == v for f, v in self.filters)]

    class FakeClient:
        def __init__(self, project):
            pass

        def collection(self, name):
            return Query(name)

    from google.cloud import firestore
    monkeypatch.setattr(firestore, "Client", FakeClient)
    from backend.providers.store_live_google import GoogleLiveStore
    store = GoogleLiveStore()
    order = TransferOrder(order_id="o", kind=OrderKind.DRUG_TRANSFER, from_facility_id="MH-0000221", to_facility_id="MH-0000223",
                          drug_id="ors", quantity=1, batches=[BatchLine(batch_no="b", quantity=1)], drive_minutes=1.0,
                          rationale="t", created_at=datetime.now(timezone.utc), created_by="solver")
    store.put("orders", "o", order)
    assert store.get("orders", "o") == order
    assert store.query("orders", {"status": OrderStatus.DRAFT}) == [order]
