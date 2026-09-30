# AushadhiNet — current state

Snapshot as of 2026-09-20. `TASK.md` is the full build log (every bug found and how it was fixed);
`tasklist.md` is what is left. Requirements are in `project.md`, design in `architecture.md`.

## What runs today

- **Local mode, zero credentials:** `uv sync --extra ml --extra dev`, seal the ledger, run backend and
  frontend (README quickstart), or `docker compose -f infra/docker-compose.yml up --build`.
- **Demo loop, through the real UI:** WhatsApp simulator report → recorded and acknowledged →
  dashboard and facility page show live stock, next-week forecast and stock-out risk → agent explains
  risk and drafts transfers → officer approves → both facilities get WhatsApp text and voice alerts.
- **Pilot data:** Nashik, 760 facilities × 16 HMIS M19 items, from the sealed synthetic ledger
  (hash `5268c2a1…`, contents-based so it matches across macOS and Linux).

## UI and languages

Redesigned frontend: Geist + Noto Sans script fonts, one teal accent (red and amber mean risk only),
light and dark themes, Phosphor icons, reduced-motion aware. Facility map on OpenStreetMap
tiles coloured by how many medicines each facility is short of (officers only; the public map
shows locations only). Seven languages end to end (UI, medicine names, dates, WhatsApp replies,
agent answers, native-script reports). Audited against the Vercel web interface guidelines.

## Verification (latest)

| Check | Result |
|---|---|
| Backend, ML, eval tests | 348 passed, 1 skipped (cloud-only ARIMA) |
| Playwright e2e, real UI sign-in | 13/13 locally and 13/13 against the live Render URLs, including 2 language tests |
| Fresh clone from GitHub (`scripts/fresh_clone_check.sh`) | passes end to end |
| `docker compose up --build` | healthy; ledger sealed at image build |
| `terraform validate` | passes (Terraform 1.16, google provider 5.45) |
| Cloud-mode code paths | tested with Google clients faked; never run against real GCP |

## Results (all logged in `eval/reports/runs.jsonl`)

| Acceptance | Result | Honest reading |
|---|---|---|
| AC4 forecasting, real HMIS frozen test | LightGBM WAPE 0.871 vs lag-1 naive 1.078, median-of-3 0.959 | Clean win (-19%). Second logged attempt; the first (1.110) lost and is kept. |
| AC6 stock-out replay, synthetic test window | stock-out weeks 10,774 → 10,131 (-6.0%) | Unmet units +0.25%: rebalances scarcity, adds no supply. ~570 transfers/week. |
| AC9 federation, Meghalaya validation | local 0.993, federated 0.996, centralised 1.000 | Ties local-only (all ~21% better than naive). Value is privacy, not accuracy. |
| App forecasts, facility-week | lag-1 naive kept | Beats best LightGBM variant 0.220 vs 0.239 on the last 13 train weeks. |
| AC3 extraction accuracy | partial | Gemini (gemini-3.1-flash-lite, AI Studio key) read on-hand quantity correctly on 220/220 rendered (not photographed) register lines across 4 scripts; English lines fully correct. Non-Latin drug names were read correctly but the offline name matcher mapped them wrongly (25.5% drug match); the Gemini-embedding matcher could not run under the free-tier 100 req/min cap. Report: eval/reports/extraction_gemini.json. Still no real-photo number. |
| AC11 cloud deploy | scripted, not run | Needs a GCP project. Runbook in README "What's not done yet". |

## Deployment

**Live (Render free tier, local mode on the sealed ledger, no GCP):**
- Frontend: https://aushadhinet-frontend.onrender.com
- Backend: https://aushadhinet-backend.onrender.com (health: `/healthz`)
- Verified 2026-09-30 after the redesign: the full Playwright suite passes against these URLs, 13/13
  (`E2E_BASE_URL=https://aushadhinet-frontend.onrender.com npx playwright test --workers=1`).
- Warm both before recording: free instances sleep, and the first request takes 30-60s.

`render.yaml` deploys both services from their Dockerfiles (Render -> New -> Blueprint).
Serving fits a 512 MB free instance: ~312 MB at startup, ~374 MB peak while proposing
transfers (was ~860 MB before the serving footprint was trimmed). Free instances sleep
when idle, so the first request after a pause takes 30-60s. This runs in local mode: the
sealed ledger, no GCP credentials. AC11 (real GCP services) is still unrun.

## Known limits

- Local state (stock, orders, outbox) is in memory; restarting the backend resets it.
- Agent in local mode is keyword dispatch over the same tools; the Gemini function-calling path is
  cloud-only and untested against the real API.
- Proposals run on demand (Orders button or agent), not on a schedule.
- Unused but tested modules: Croston/ensemble forecasters, calibration, reconciliation.
- One unused variable in `ml/generator/ledger.py` is deliberately left alone (sealed generator).
