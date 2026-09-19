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
| GET | `/simulator/contacts` | Local mode only. Pilot-district facilities with their dev WhatsApp numbers. |
| GET | `/simulator/outbox?phone=...` | Local mode only. Replies the system would have sent to that number. |

Inbound messages from a registered facility number are parsed and acknowledged; `YES` confirms that
facility's pending (low-confidence) records; unregistered numbers get a refusal.

## Officer (requires `block`, `district`, or `state` role)

| Method | Path | Description |
|---|---|---|
| GET | `/officer/orders/{district_id}` | Orders touching a district (jurisdiction-checked). |
| POST | `/officer/propose/{district_id}` | Run the transfer solver; store results as drafts, expiring the district's earlier drafts. |
| POST | `/officer/orders/{id}/approve` | Approve a draft: signs it, sends WhatsApp + voice alerts to both facilities. Idempotent. 409 if not a draft. |
| POST | `/officer/orders/{id}/reject` | Reject a draft. 409 if already approved. |
| GET | `/officer/districts/{district_id}/facilities` | Facilities in a district with an at-risk flag. |
| GET | `/officer/facility/{facility_id}` | Latest stock, next-week forecast and stock-out probability for one facility. |
| POST | `/officer/escalation/sweep` | `state` role only. Escalates overdue draft orders one level. |

Jurisdiction is always derived from the order's own facilities (facility directory lookup), never from
a caller-supplied district. A cross-district order needs an officer covering both districts.
| POST | `/agent/ask` | Ask the officer agent a question (`{"question": "..."}`). Cannot approve or send anything — see backend/agent/tools.py. |

## Public (no auth)

| Method | Path | Description |
|---|---|---|
| GET | `/public/district-summary` | Per district: facilities reporting, facilities with any drug under one week of cover, and that count per drug. No facility-level identifiers. |

## Error shape

Every error response is `{"detail": "..."}`. `ProviderError` (an external-service failure) → 502.
A Pydantic validation error → 422. Missing/invalid auth → 401/403.
