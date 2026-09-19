"""DoD test for backend/api/agent_api.py (added alongside frontend step 40
since lib/api.ts calls it)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app


def test_agent_ask_requires_auth():
    client = TestClient(create_app())
    response = client.post("/agent/ask", json={"question": "hello"})
    assert response.status_code == 401


def test_agent_ask_returns_answer_for_authorized_officer():
    client = TestClient(create_app())
    response = client.post(
        "/agent/ask", json={"question": "hello"},
        headers={"Authorization": "Bearer dev:u1:district:mh/nashik"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "text" in body and "cited_ids" in body


def test_agent_ask_rejects_facility_role():
    client = TestClient(create_app())
    response = client.post(
        "/agent/ask", json={"question": "hello"},
        headers={"Authorization": "Bearer dev:u1:facility:mh/nashik"},
    )
    assert response.status_code == 403
