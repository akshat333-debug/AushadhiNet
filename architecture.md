# AushadhiNet — Architecture & Tech Stack (Gate 2)

Requirements: `project.md`. Data: `data/README.md`. Layer diagram: `docs/review1/fig2_architecture.png`.

## 1. Tech stack (versions checked on PyPI/npm, 18 Sep 2026)
| Area | Choice | Why |
|---|---|---|
| Runtime | Python 3.12 (managed by `uv`), Node 24 | 3.12 is supported by every ML dependency. Flower requires Python below 4. |
| Backend API | FastAPI + Uvicorn, Pydantic v2 | Async webhooks, and schemas shared with the Gemini structured output |
| Frontend | Next.js (App Router) + TypeScript, Tailwind, `@vis.gl/react-google-maps`, PWA via service worker | Officer app, map dashboard, WhatsApp simulator and public page in one app |
| Live state | Firestore (Firebase emulator locally) | Real-time listeners drive the dashboard |
| History / analytics | BigQuery (DuckDB locally) | Same SQL dialect subset; BigQuery ML ARIMA_PLUS baseline |
| Queue | Pub/Sub (in-process asyncio queue locally) | Decouples the webhook from slow AI calls |
| GenAI | `google-genai` 2.x → Gemini (model name set in `GEMINI_MODEL`); works with either an AI Studio key or Vertex AI | Extraction, the agent, explanations |
| Speech | `google-cloud-speech` v2, Chirp 2 model | Marathi, Hindi and English voice notes |
| Translation / TTS | Cloud Translation v3, Cloud Text-to-Speech | Local-language alerts |
| Embeddings | Vertex AI text embeddings + Vector Search (numpy cosine search locally) | NLEM drug-name normalisation |
| Forecasting | `lightgbm` 4.7, `timesfm` 3.0, `statsforecast` (Croston/SBA, seasonal naive), BigQuery ML ARIMA_PLUS | Ensemble plus baselines |
| Optimisation | `ortools` 9.15 (`SimpleMinCostFlow`, CP-SAT for deputation) | Fast, exact, and Google's own solver |
| Agent | `google-adk` 2.x | Gemini function calling with tool governance |
| Federation | `flwr` 1.37 (FedProx strategy) + a DP clipping/noise wrapper | Standard, runs locally and on Vertex |
| Messaging | Twilio WhatsApp sandbox (`twilio` SDK) | Real WhatsApp in hours; the adapter can be swapped to the Meta Cloud API |
| Signing | Cloud KMS (HMAC-SHA256 with a local key when offline) | Tamper-evident transfer orders |
| Infra | Docker Compose (local), Cloud Run, Terraform, Cloud Build | One command locally; serverless in the cloud |
| Tests | pytest, pytest-asyncio, Playwright | Unit, contract and end-to-end tests |

## 2. Provider pattern (runs offline, same code path)
Every Google service sits behind one small interface in `backend/providers/`, with exactly two implementations: `google` and `local`. `config.py` reads `AUSHADHI_MODE=local|cloud`. In local mode:
- Speech uses fixture transcripts.
- Extraction calls Gemini if `GEMINI_API_KEY` is set; otherwise it replays recorded responses.
- Stores use the Firestore emulator and DuckDB.
- Signing uses HMAC.

Placeholders live in `.env.example` (`GCP_PROJECT=REPLACE_ME`, etc.). No other file reads the environment directly.

## 3. Repository layout
```
backend/            FastAPI app
  api/              routes: webhooks (twilio, ivr, simulator), officer, public
  providers/        speech, llm, embed, translate, tts, store_live, store_history, queue, sign, messaging
  ingest/           extraction schemas, confidence gate, NLEM matcher, confirmation cards
  domain/           Pydantic models: Facility, StockRecord, BedCensus, CheckIn, Forecast, TransferOrder
  agent/            ADK agent, tools (read-only + propose_order), audit log
  action/           order signing, alerts, escalation ladder
ml/
  generator/        SEALED synthetic ledger (stock/beds/attendance) — nothing else may import it
  data/             HMIS parsers (M19 stock flows, M10/M11 disease), facility graph, weather
  forecast/         baselines, croston, lgbm, timesfm, ensemble, calibration, reconcile
  optimize/         min-cost-flow transfers, deputation, referral
  federated/        flower client/server, fedprox + DP, experiments
eval/               protocol.lock (splits, seeds, generator hash), runners, reports
frontend/           Next.js app
infra/              docker-compose.yml, Dockerfiles, terraform/ (state module), cloudbuild.yaml
tests/              mirrors packages; e2e/ (Playwright)
data/               README + manifest (raw/ is gitignored)
docs/               review1/ + api docs
```

## 4. Data flow (Input → Processing → Store → ML → Output)
1. WhatsApp message → Twilio → `POST /webhooks/twilio` (signature verified) → 200 returned immediately → message queued.
2. Worker: media is downloaded (type and size checked) → Chirp for audio or Gemini for images → a `StockRecord` / `BedCensus` / `CheckIn` with a confidence value per field.
3. Confidence gate: any field under the threshold (default 0.85) → confirmation card sent back → the record stays `pending`. Otherwise it is `confirmed`.
4. Confirmed record → Firestore (live) + BigQuery (history).
5. Nightly job, or a trigger on a new record: forecast → stock-out probabilities → the solver proposes orders → orders stored as `draft`.
6. Officer PWA and agent: queries go through read-only tools; `propose_order` can only create drafts. Only a human click on `POST /orders/{id}/approve` (role checked) moves an order to `approved`.
7. Approved order → signed → alerts sent in the recipient's language plus a route plan → escalation timer starts → dashboard updates in real time.
8. Federation (offline job): each state client trains on its own partition → sends clipped, noised updates → Flower server aggregates with FedProx → global model is sent back.

## 5. Evaluation integrity (enforced in code)
- `eval/protocol.lock` fixes the time windows, the held-out district (Dhule) and held-out state (Meghalaya), the seeds and the generator's content hash. It is committed before any file under `ml/forecast/` exists.
- `tests/test_isolation.py`: an AST scan fails the build if any module outside `ml/generator/` and `eval/` imports `ml.generator`.
- Test-window scoring happens only through `eval/run_final.py`, which appends to `eval/reports/runs.jsonl`. Every run is logged, so re-scoring is visible.

## 6. Security & privacy pass (before any code)
| Risk | Control |
|---|---|
| Forged webhooks | Twilio `X-Twilio-Signature` validation; reject unsigned requests |
| Malicious uploads | Allow-list of MIME types (jpeg/png/ogg/amr/mp3), 10 MB cap, never executed, stored in a private bucket |
| AuthN / AuthZ | Firebase Auth. Custom claims: role (facility/block/district/state/public) and jurisdiction. Every officer route checks role and jurisdiction |
| Agent misuse / prompt injection from extracted text | The agent has read-only tools plus draft-only `propose_order`. Extracted text is passed as data, not instructions. There is no tool that sends messages or approves orders |
| Secrets | `.env` only (gitignored), Secret Manager in the cloud, `.env.example` holds placeholders |
| Injection | Parameterised BigQuery/DuckDB queries only; Pydantic validation at every boundary; React escaping; no `dangerouslySetInnerHTML` |
| CSRF | Bearer-token API (no cookies) for officer routes |
| Personal data | Staff names and phone numbers are stored per state only. The public view is aggregate-only. Phone numbers are hashed in logs |
| Order tampering | Orders are signed; signatures are verified on delivery and display |
| Data sovereignty | One GCP project per state; only DP-noised updates leave it; VPC Service Controls perimeter (Terraform) |
| Dependencies | Pinned lockfiles (`uv.lock`, `package-lock.json`); `pip-audit` and `npm audit` in CI |
| Audit | Every agent tool call, approval and alert goes to an append-only audit table |

## 7. Build approach
Modular path (ML + many integrations). Next artefact after this gate: `modular-plan.md`, drafted by an Opus agent. Build order starts with `eval/protocol.lock` + `ml/generator/`, then `ml/data/` (HMIS M19 parser) and baselines, then the rest (see the approved plan). Each file is built with `tdd`.

## 8. Open items (non-blocking)
- `GEMINI_MODEL` default: pick the newest Flash model available when credits arrive; for now it is set from the env only.
- Chirp 2 region availability for Marathi: verify on the GCP console once the project exists. The fallback is the `chirp` model or `latest_long`.
