# AushadhiNet API reference

Base URL: `http://localhost:8000` (local), or the Cloud Run URL once deployed.
Auth: `Authorization: Bearer dev:<uid>:<role>:<jurisdiction>` in local mode (backend/deps.py);
a real Firebase Auth ID token in cloud mode. `role` is one of `facility`, `block`, `district`, `state`, `public`.

## Capture (no auth — trusted channel or public webhook)

| Method | Path | Description |
|---|---|---|
| POST | `/webhooks/twilio` | Twilio WhatsApp sandbox webhook. Signature-verified in cloud mode. Queues the message; returns in <1s. |
| POST | `/simulator/message` | Local mode, or cloud with `DEMO_MODE`. Web WhatsApp simulator (text, photo, voice note, shared location as `latitude`/`longitude`); same handler as Twilio (`publish_inbound_message`). Photos and voice notes capped at 20 a minute (429). |
| GET | `/simulator/contacts` | Local or demo mode. Pilot-district facilities with their dev WhatsApp numbers. |
| GET | `/simulator/outbox?phone=...` | Local or demo mode. Replies the system would have sent to that number. |

Inbound messages from a registered facility number are parsed and acknowledged; `YES` confirms that
facility's pending (low-confidence) records; unregistered numbers get a refusal.

## Officer (requires `block`, `district`, or `state` role)

| Method | Path | Description |
|---|---|---|
| GET | `/officer/orders/{district_id}` | Orders touching a district (jurisdiction-checked), with facility names, the destination's days of cover and a district-wide-gap flag; most urgent first, expired drafts left out. |
| POST | `/officer/propose/{district_id}` | Run the transfer solver; store results as drafts, expiring the district's earlier drafts. |
| POST | `/officer/orders/{id}/approve` | Approve a draft: 409 unless the source physically holds the units, not already promised; then signs it and sends WhatsApp + voice alerts to both facilities (registered numbers), each in its contact's language. 502 if the alerts fail: the order stays approved and approving again resends. Idempotent. |
| POST | `/officer/orders/{id}/reject` | Reject a draft. 409 if already approved. |
| POST | `/officer/orders/{id}/dispatched` | Mark the units sent (the source can reply `SENT <code>`); until then they stay reserved at the source. |
| POST | `/officer/orders/{id}/received` | Mark the units received (the destination can reply `RECEIVED <code>`). |
| POST | `/officer/capacity/approve` | `{kind, from_id, to_id, role}`: approve one of today's referral or deputation suggestions into a signed order (role and head count signed). 409 if no longer suggested. |
| GET | `/officer/districts/{district_id}/facilities` | Facilities in a district with an at-risk flag. |
| GET | `/officer/capacity/{district_id}` | Today's beds and staff: occupancy, facilities at least 90% full with referral suggestions, staff on site vs posts, off-site check-ins, deputation suggestions (`backend/capacity.py`). Facilities that have not reported show a generated baseline in local and demo mode (`demo_baseline: true`). |
| GET | `/officer/facility/{facility_id}` | Latest stock, next-week forecast and stock-out probability for one facility. |
| POST | `/officer/escalation/sweep` | `state` role only. Escalates overdue draft orders one level. |

Jurisdiction is always derived from the order's own facilities (facility directory lookup), never from
a caller-supplied district. A cross-district order needs an officer covering both districts.
| POST | `/agent/ask` | Ask the officer agent a question (`{"question": "..."}`). Cannot approve or send anything — see backend/agent/tools.py. |

## Internal

| Method | Path | Description |
|---|---|---|
| POST | `/internal/pubsub/ingest` | Cloud mode only. Pub/Sub push target for the ingest worker. Requires a Google OIDC token for `PUBSUB_PUSH_SERVICE_ACCOUNT` with audience `PUBSUB_PUSH_AUDIENCE`; 503 until both are configured. |

## Public (no auth)

| Method | Path | Description |
|---|---|---|
| GET | `/public/district-summary` | Per district: facilities reporting, facilities with any drug under one week of cover, that count per drug, medicines short district-wide (`escalate`, with `procurement_units`) and `facilities_needing_transfer`. No facility-level identifiers. |
| GET | `/public/federated` | The model the two-process federation demo trained (`ml/federated/demo.py`), loaded and applied: estimate vs actual units for Meghalaya's latest validation month, with its WAPE. |
| GET | `/public/voice/{token}.ogg` | A spoken order alert, for Twilio to fetch; the token is random and sent only to the two facilities. |
| GET | `/public/coverage` | Every state in the MoHFW facility directory: facility and district counts, and how many districts are live. Counts only. |

## Error shape

Every error response is `{"detail": "..."}`. `ProviderError` (an external-service failure) → 502.
A Pydantic validation error → 422. Missing/invalid auth → 401/403.
