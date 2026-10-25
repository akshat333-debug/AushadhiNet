# AushadhiNet — current state

Snapshot as of 2026-10-25. Team **Visible** is a top-10 finalist in Track 3 (see `HACKATHON.md`).
`PROGRESS.md` is what is done and why; `tasklist.md` is what is left; `docs/build-log.md` is the full
build log (every bug found and how it was fixed). Requirements: `project.md`; design: `architecture.md`.

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
| Backend, ML, eval tests | 333 passed (2026-10-24, with the gcp extra) |
| Playwright e2e, real UI sign-in | 14/14 locally and 14/14 on the live Render URLs (2026-10-24, includes the photo test) |
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
| AC3 extraction accuracy | measured on synthetic renders | Gemini (gemini-3.1-flash-lite) on 206 of 220 rendered register lines (14 hit free-tier 429s), 4 scripts: medicine 98.1% (Bengali 92.2%, others 100%), quantity 100%, batch 100% outside Devanagari. Devanagari batch scores 0% because the render font has no Latin "B" (drawn as a box), so the label is unreadable in the image itself: an eval-data bug, not a read error. Images are rendered text, not photographs; no real-photo number yet. Report: eval/reports/extraction_gemini.json. |
| AC11 cloud deploy | met | Terraform + Cloud Build deployed to Cloud Run on 2026-10-24; see Deployment below. |

## Deployment

**Live on Google Cloud (2026-10-24, project `aushadhinet`, asia-south1, cloud mode + `DEMO_MODE`):**
- Frontend: https://aushadhinet-frontend-449585498230.asia-south1.run.app
- Backend: https://aushadhinet-backend-449585498230.asia-south1.run.app (health: `/health`; Cloud Run reserves `/healthz`)
- Real services: Firestore (760 contacts, 12,160 stock rows seeded with BulkWriter), BigQuery
  history, Pub/Sub push, KMS order signing, Secret Manager, Vertex AI embeddings, Gemini photos.
- Verified: Playwright against the Cloud Run URLs (2026-10-25, build 38d066c): 13/14 in the full
  run; the offline test was flaky on a fixed 1.5 s wait, now waits for the service worker and
  passes 5/5; a 3-line register
  photo read correctly; the agent's Gemini note appears on live answers (about 12 s an answer).
- Limits: backend max 1 instance (in-memory simulator outbox; caps cost), frontend max 2, both scale
  to zero. Budget alert Rs 850/month (alerts only).
- Not configured: Firebase Auth and Twilio (demo sign-in and the simulator stand in), Maps
  (straight-line travel time).


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
- Register photos: Gemini reads every line (checked against the real Developer API through the
  simulator UI). On Render this needs `GEMINI_API_KEY` set in the dashboard; without it a photo
  gets a "please type it" reply. Every photo read waits for the nurse's YES.
- Free Gemini tier: 100 embedding calls a minute, so NLEM name matching uses the offline matcher
  (with Indic-script names from `backend/i18n.py`) rather than Gemini embeddings.
- Proposals run on demand (Orders button or agent), not on a schedule.
- One unused variable in `ml/generator/ledger.py` is deliberately left alone (sealed generator).
