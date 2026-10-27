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
| Forecasting | `lightgbm` 4.7 plus naive baselines | LightGBM (offline eval), lag-1 naive (served) |
| Optimisation | `ortools` 9.15 (`SimpleMinCostFlow`, CP-SAT for deputation) | Fast, exact, and Google's own solver |
| Agent | `google-genai` function calling (manual loop) + fixed templates | Templates answer common questions predictably; Gemini picks among read-only, jurisdiction-checked functions for the rest |
| Federation | `flwr` 1.37 client API (FedProx) + a clipping/noise wrapper, run as an in-process simulation; scored runs use noise 0, so no DP guarantee | Standard; a real deployment would run one client per state project |
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
  runtime.py        inbound-message routing (stock, BEDS, location check-ins), contacts registry, risk helpers, draft proposals; local seeding
  capacity.py       beds and staff per district: full facilities + referrals, staff gaps + deputations (demo baseline in demo mode)
  api/              routes: webhooks (twilio), simulator (local, or cloud demo mode), officer, public, agent, pubsub push (cloud)
  providers/        speech, llm, embed, translate, tts, store_live, store_history, queue, sign, messaging
  ingest/           extraction schemas, confidence gate, NLEM matcher, confirmation cards
  domain/           Pydantic models: Facility, Contact, StockRecord, BedCensus, CheckIn, Forecast, TransferOrder
  agent/            agent, jurisdiction-checked tools (reads + draft-only proposals), audit log
  action/           order signing, alerts, escalation ladder
ml/
  generator/        SEALED synthetic ledger (stock/beds/attendance) — nothing else may import it
  data/             HMIS parsers (M19 stock flows, M10/M11 disease), facility graph, weather
  forecast/         baselines, features, lgbm, stockout, service
  optimize/         min-cost-flow transfers, deputation, referral
  federated/        flower client/server, fedprox, clipping/noise wrapper, experiments (simulation)
eval/               protocol.lock (splits, seeds, generator hash), tuning (val/dev only), scoring runners, replay simulator, reports
frontend/           Next.js app
infra/              docker-compose.yml, Dockerfiles, terraform/ (state module), cloudbuild.yaml
tests/              mirrors packages; e2e/ (Playwright)
data/               README, manifest and raw/ (open-licence source files, committed); synthetic/ is built, not committed
docs/               review1/, api/, finale/ (demo script, Q&A), pitch/ (deck, video), screenshots/
```

## 4. Data flow (Input → Processing → Store → ML → Output)
1. WhatsApp message → Twilio → `POST /webhooks/twilio` (signature verified) → 200 returned immediately → message queued. The local web simulator posts to the same entry point.
2. Worker (cloud: Pub/Sub pushes to `/internal/pubsub/ingest`, OIDC-verified; local: in-process queue): sender looked up in the contacts registry → media is downloaded (type and size checked) → Chirp for audio or Gemini for images → a `StockRecord` / `BedCensus` / `CheckIn` with a confidence value per field.
3. Confidence gate: any field under the threshold (default 0.85) → confirmation card sent back → the record stays `pending`. Otherwise it is `confirmed`.
4. Confirmed record → Firestore (live) + BigQuery (history).
5. When an officer clicks "Propose transfers" or asks the agent: next-week forecast from reported history → stock-out probabilities using live stock → the solver proposes transfers (donors keep 2 weeks of cover) → stored as `draft`, replacing the district's earlier drafts. No scheduled job runs this yet.
6. Officer PWA and agent: queries go through read-only tools; `propose_order` can only create drafts. Only a human click on `POST /officer/orders/{id}/approve` (role and jurisdiction checked against the order's own facilities) moves an order to `approved`.
7. Beds and staff: `BEDS 4/6` writes a `BedCensus`; a shared location writes a `CheckIn` with `geofence_ok` (200 m). `GET /officer/capacity/{district}` runs the referral solver on facilities at least 90% full and the CP-SAT deputation solver on roles nobody covers today; an officer approves one into a signed REFERRAL or DEPUTATION order (role and head count signed).
8. Stock movement: approved units stay reserved at the source until it replies `SENT <code>`; approval counts only physical stock (incoming units count for planning, not for sending onward); the destination replies `RECEIVED <code>`.
9. Demand: next week's demand is a facility's own use between two of its counts a day or more apart (`backend/runtime.py: recent_use`), else the ledger's last week.
10. Federation demo: `ml/federated/node.py` runs one state per process (own files only); `ml/federated/demo.py` aggregates counts, sums and FedProx updates into `backend/federated/model.npz`, served by `GET /public/federated`.
8. Approved order → signed → alerts sent in the recipient's language plus a route plan → escalation timer starts → dashboard updates in real time.
9. Federation (offline simulation, not deployed): each state client trains on its own partition → sends model updates (clipping and noise available, noise 0 in scored runs) → the server aggregates with FedProx → the global model is sent back. The app's forecasts do not use it.

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
| Personal data | Staff names and phone numbers are stored per state only. The public view is aggregate-only. Contact numbers sit in the contacts registry (alerts go to them); stock, bed and check-in records and logs carry a hash |
| Order tampering | Orders are signed; signatures are verified on delivery and display |
| Data sovereignty | Planned: one GCP project per state, with only model updates leaving it. Today one project serves the demo |
| Dependencies | Pinned lockfiles (`uv.lock`, `package-lock.json`); `pip-audit` and `npm audit` in CI |
| Audit | Every agent tool call, approval and alert goes to an append-only audit table |

## 7. Build approach
Modular path (ML + many integrations). Next artefact after this gate: `modular-plan.md`, drafted by an Opus agent. Build order starts with `eval/protocol.lock` + `ml/generator/`, then `ml/data/` (HMIS M19 parser) and baselines, then the rest (see the approved plan). Each file is built with `tdd`.

## 8. Open items (non-blocking)
- `GEMINI_MODEL` default: pick the newest Flash model available when credits arrive; for now it is set from the env only.
- Chirp 2 region availability for Marathi: verify on the GCP console once the project exists. The fallback is the `chirp` model or `latest_long`.
