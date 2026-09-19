# AushadhiNet API reference

Base URL: `http://localhost:8000` (local), or the Cloud Run URL once deployed.
Auth: `Authorization: Bearer dev:<uid>:<role>:<jurisdiction>` in local mode (backend/deps.py);
a real Firebase Auth ID token in cloud mode. `role` is one of `facility`, `block`, `district`, `state`, `public`.

## Capture (no auth — trusted channel or public webhook)

| Method | Path | Description |
|---|---|---|
| POST | `/webhooks/twilio` | Twilio WhatsApp sandbox webhook. Signature-verified in cloud mode. Queues the message; returns in <1s. |
| POST | `/webhooks/ivr` | Dialogflow CX fulfillment webhook for the IVR channel. |
| POST | `/simulator/message` | Web WhatsApp simulator (project.md's demo channel). Same handler as Twilio (`publish_inbound_message`). |

## Officer (requires `block`, `district`, or `state` role)

| Method | Path | Description |
|---|---|---|
| GET | `/officer/orders/{district_id}` | List orders in a district (jurisdiction-checked). |
| POST | `/officer/orders/{id}/approve?district_id=...` | Approve a draft order: signs it, moves to `approved`. Idempotent. |
| POST | `/officer/orders/{id}/reject?district_id=...` | Reject a draft order. |
| POST | `/agent/ask` | Ask the officer agent a question (`{"question": "..."}`). Cannot approve or send anything — see backend/agent/tools.py. |

## Public (no auth)

| Method | Path | Description |
|---|---|---|
| GET | `/public/district-summary` | Aggregate district-level stock-out-risk counts. No facility-level identifiers ever appear here. |

## Error shape

Every error response is `{"detail": "..."}`. `ProviderError` (an external-service failure) → 502.
A Pydantic validation error → 422. Missing/invalid auth → 401/403.
