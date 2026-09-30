# AushadhiNet

Federated AI for India's last-mile health resource network — medicines, beds and staff.
Built for **Build with AI: Code for Communities** (Second Edition), Problem Statement 03 — Smart Health & Supply Chain Resilience.

Full requirements: [project.md](project.md). Architecture and stack: [architecture.md](architecture.md).
Build plan and file-by-file order: [modular-plan.md](modular-plan.md). Progress log with every bug found
and fixed along the way: [TASK.md](TASK.md). Current status and results: [state.md](state.md).
What is left: [tasklist.md](tasklist.md). Original research document: [docs/review1/](docs/review1/).

## What it does

A nurse reports medicine stock, bed counts, and their own presence at a Primary Health Centre by
WhatsApp voice note, photo, or text, in Marathi, Hindi, or English. Gemini and Chirp turn that into
structured records with a confidence score per field — anything uncertain gets a one-tap confirmation
card, never a silent guess. A forecasting model predicts stock-out risk weeks ahead from real government
health data. An OR-Tools solver turns that risk into a concrete transfer order between nearby facilities.
A district officer reviews it — with an AI agent that can explain the risk and draft a proposal, but
cannot approve or send anything itself — and one click signs it and sends alerts in the recipient's own
language.

## Quickstart (local, zero cloud credentials)

Requires: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
# 1. Backend
uv sync --extra ml --extra dev    # add --extra gcp only for cloud mode
cp .env.example .env               # defaults are all local-mode; no keys needed
uv run python -m eval.seal_generator   # rebuilds data/synthetic/, fails if hash != protocol.lock
uv run pytest -q                   # ~320 tests, a few minutes
uv run uvicorn backend.app:app --reload --port 8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                        # http://localhost:3000
```

On startup (local mode) the backend seeds Nashik's 760 facilities with the latest week of the sealed
synthetic ledger and gives each a dev WhatsApp number. Demo walkthrough at `http://localhost:3000`:

1. **Simulator** (`/sim`): pick a facility, send `ORS 0`. The reply confirms what was recorded.
2. **Sign in** (top right): "District officer, Nashik".
3. **Dashboard**: India → Maharashtra → Nashik → a facility shows live stock, next-week demand and
   stock-out risk. Alerts list drugs under one week of cover.
4. **Agent** (`/agent`): "Which facilities are at risk?", "Why is MH-0000221 at risk for ORS?",
   "Propose transfers" (drafts only).
5. **Orders** (`/orders`): Propose transfers, approve one. Both facilities get a WhatsApp text and
   voice note, visible in the simulator's outbox for that facility.
6. Sign in as "District officer, Dhule" and try the same facility: refused, in the UI and in the agent.

`/public` is the no-login transparency view (district counts only).

**Languages:** English, हिन्दी, मराठी, বাংলা, தமிழ், తెలుగు, ಕನ್ನಡ (switcher in the top bar). The whole UI,
medicine names, dates, WhatsApp replies, confirmation cards and local-mode agent answers follow
the chosen language, and reports can be typed in any of these scripts (`ओआरएस 50`, `झिंक ५`).
Translations were written for this project and should be reviewed by native speakers before a
real rollout. Ambiguous names such as "IFA" (four products) always get a confirmation card.

### Docker

`infra/docker-compose.yml` runs the same two services in containers (backend on locked
dependencies, frontend as a production `next build`):

```bash
docker compose -f infra/docker-compose.yml up --build
```

On every start the backend regenerates the synthetic ledger and checks it against the seal in
`eval/protocol.lock`; it refuses to serve if the hash differs. First start takes a minute or two.
Verified on 2026-09-19: the stack came up healthy (backend about 860 MB RAM) and all 11 Playwright
tests passed against the containers.

## Rebuilding the synthetic data

The evaluation depends on real public data (`data/raw/`, downloaded and checksum-verified — see
[data/README.md](data/README.md)) and a **sealed** synthetic ledger (`data/synthetic/`, gitignored,
regenerated deterministically):

```bash
uv run python -m eval.seal_generator     # regenerates data/synthetic/*.parquet, verifies the hash
                                          # already locked in eval/protocol.lock; refuses silently
                                          # if the output has changed since sealing (use --force
                                          # only if the change is a deliberate, reviewed one)
```

## Evaluation

```bash
uv run python -m eval.run_final           # real-HMIS frozen test: LightGBM vs naive baselines
uv run python -m eval.run_replay          # solver vs no-transfer status quo, frozen synthetic test window
uv run python -m eval.run_federated_eval  # local-only vs federated vs centralised (Meghalaya)
```

Every run appends to `eval/reports/runs.jsonl` — nothing is ever overwritten, so the full history of
every scored attempt is auditable. **Current honest results** (see TASK.md for full detail and the real
numbers behind these headlines):

- Forecasting (real HMIS, Maharashtra, frozen test Sep 2019 – Feb 2020, 2,501 district-drug-months):
  LightGBM WAPE **0.871** vs lag-1 naive 1.078 and median-of-3 0.959 (19% better than naive). This is
  the second scored attempt; the first (L2 objective, WAPE 1.110, lost to naive) stays in `runs.jsonl`.
  The fix (L1 objective, since WAPE rewards the median) was chosen on the validation window only
  (`eval/tune_val.py`).
- Federation (Meghalaya, validation split, 541 rows): log-space linear head. Local-only 0.993,
  federated 0.996, centralised 1.000; all about 21% better than lag-1 naive (1.261). Federation
  **ties** local-only, it does not beat it. Chosen on an inner split of train (`eval/tune_federated.py`)
  so this validation number was not tuned against. Earlier raw-space run: 1.122 / 1.182 / 1.336.
- App forecasts (facility × week, synthetic ledger) use lag-1 naive, not LightGBM. On the last 13
  training weeks naive scores WAPE 0.220 vs 0.239 for the best LightGBM variant (residual on
  median-of-3) and 0.307 for the monthly model's settings, so the app uses whichever measured best at its
  grain. (Re-measured after the drug-mapping re-seal; the pre-seal numbers were 0.243 / 0.255 / 0.397.)
- Stock-out replay (AC6, synthetic Nashik ledger, frozen 26-week test window, 760 facilities x 16
  items): weekly solver transfers cut facility-weeks with a stock-out from **10,774 to 10,131 (-6.0%)**
  versus no lateral transfers. Total unmet demand does not fall (+0.25%): redistribution spreads scarce
  stock so fewer facilities run dry, it does not add supply, and fill rate is about 68% either way.
  It took 14,815 transfers (about 570 a week), too many to approve one by one. Both arms run through
  `eval/replay_sim.py` with identical pre-drawn demand, shocks and delays; the solver sees only
  reported history. `cover_weeks=2` was chosen on the 26 weeks before the test window
  (`eval/tune_replay.py`); the old donor rule made stock-outs worse there (+291 weeks). The previous
  replay never called the solver and scored identically to baseline.

## Testing

```bash
uv run pytest -q                          # backend + ml + eval: ~340 tests
cd frontend && npx playwright test        # frontend e2e, needs both dev servers (playwright.config.ts starts them)
```

## Project layout

```
backend/     FastAPI app: domain models, providers (local/google), ingest, agent, action, API, runtime wiring
ml/          data parsers, sealed synthetic generator, forecasting, optimisation, federated learning
eval/        the frozen evaluation protocol and every scoring script
frontend/    Next.js officer PWA, WhatsApp simulator, public transparency view
infra/       Dockerfiles, docker-compose, Terraform (per-state GCP project), Cloud Build
data/        provenance, licences, manifest, and the raw open-licence source files
docs/        the original Review-1 research document, and API reference
tests/       mirrors every package above, plus frontend/tests/e2e
```

## Design decisions worth knowing

- **Every Google Cloud service has a local fallback** behind one two-implementation seam
  (`backend/providers/`), so the entire system runs with zero credentials. Swapping to real Gemini,
  Chirp, Firestore, BigQuery, etc. is an `.env` change (`AUSHADHI_MODE=cloud`), not a rewrite.
- **The evaluation protocol was frozen before any model existed** (`eval/protocol.lock`), and the
  synthetic data generator is sealed with a content hash — an automated test
  (`tests/test_isolation.py`) fails the build if any forecasting code ever imports the generator.
- **The officer agent structurally cannot approve or send anything.** Its tool registry has no such
  tool at all — verified by name inspection and a real prompt-injection test, not by asking the model
  nicely.
- **Real, honest results are reported even when they're not flattering.** See TASK.md for a full list
  of bugs found and fixed along the way, and the current forecasting/federation results above.

## What's not done yet

- Local-mode state (stock, orders, outbox) is in memory and resets when the backend restarts.
- Built and tested but not called by the app: the Croston/ensemble forecasters, calibration,
  and hierarchical reconciliation.

- The 220 handwriting-extraction evaluation images are **programmatically rendered text**, not real
  photographs of handwritten registers (see `scripts/generate_labelled_registers.py`'s docstring). Real
  extraction accuracy needs either real photos + annotation, or a real Gemini key in cloud mode.
- Cloud deployment (AC11) is ready but not run: it needs a GCP project. Order of operations:
  `terraform apply` in `infra/terraform/state-module` (APIs, Firestore, BigQuery tables, Pub/Sub, KMS,
  Artifact Registry, service accounts, secret containers), add the Twilio and Gemini secret values,
  `gcloud builds submit --config infra/cloudbuild.yaml` (see its header for the two-pass URL step),
  `terraform apply -var backend_url=...` to turn on Pub/Sub push, then
  `AUSHADHI_MODE=cloud python -m backend.runtime seed` to load the pilot district into Firestore.
  Cloud code paths are tested with the Google clients faked (`tests/backend/test_cloud_mode.py`), not
  against real services.
- Federation ties but does not beat local-only training for the data-poor state; its value here is
  matching local accuracy without pooling raw data, not beating it.
