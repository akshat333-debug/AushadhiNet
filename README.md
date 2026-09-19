# AushadhiNet

Federated AI for India's last-mile health resource network — medicines, beds and staff.
Built for **Build with AI: Code for Communities** (Second Edition), Problem Statement 03 — Smart Health & Supply Chain Resilience.

Full requirements: [project.md](project.md). Architecture and stack: [architecture.md](architecture.md).
Build plan and file-by-file order: [modular-plan.md](modular-plan.md). Progress log with every bug found
and fixed along the way: [TASK.md](TASK.md). Original research document: [docs/review1/](docs/review1/).

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
uv run pytest -q                   # ~300 tests, a few minutes
uv run uvicorn backend.app:app --reload --port 8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                        # http://localhost:3000
```

Open `http://localhost:3000/sim` to try the WhatsApp simulator, `/orders` to see the officer approval
queue, `/agent` to ask the officer agent a question, and `/public` for the public transparency view.

### Docker

`infra/docker-compose.yml` runs the same two services in containers:

```bash
cd infra && docker compose up --build
```

**Honest note**: this compose file was written and structurally tested (`tests/infra/test_compose.py`),
but never run end-to-end in the sandbox this project was built in — the Docker daemon wasn't running
there. The credential-free local run it packages *was* verified for real: the Playwright end-to-end
suite (`frontend/tests/e2e/`) ran against real `uvicorn` + `next dev` processes with zero GCP credentials
and all 6 tests passed. Run `docker compose up --build` yourself before relying on it for a demo.

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
uv run python -m eval.run_replay          # solver-assisted vs monthly-indent stock-out replay
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
  training weeks naive scores WAPE 0.243 vs 0.255 for the best LightGBM variant (residual on last
  week) and 0.397 for the monthly model's settings, so the app uses whichever measured best at its grain.

## Testing

```bash
uv run pytest -q                          # backend + ml + eval: ~285 tests
cd frontend && npx playwright test        # frontend e2e, needs both dev servers (playwright.config.ts starts them)
```

## Project layout

```
backend/     FastAPI app: domain models, provider abstractions (local/google), ingest, agent, action, API
ml/          data parsers, sealed synthetic generator, forecasting, optimisation, federated learning
eval/        the frozen evaluation protocol and every scoring script
frontend/    Next.js officer PWA, WhatsApp simulator, public transparency view
infra/       Dockerfiles, docker-compose, Terraform (per-state GCP project), Cloud Build
data/        provenance, licenses, and the download manifest (raw data itself is gitignored)
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

- The 220 handwriting-extraction evaluation images are **programmatically rendered text**, not real
  photographs of handwritten registers (see `scripts/generate_labelled_registers.py`'s docstring). Real
  extraction accuracy needs either real photos + annotation, or a real Gemini key in cloud mode.
- Terraform (`infra/terraform/`) and `docker compose up` are written but not run end-to-end in this
  environment — see the honest notes above and in TASK.md.
- Federation ties but does not beat local-only training for the data-poor state; its value here is
  matching local accuracy without pooling raw data, not beating it.
