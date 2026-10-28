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
| Backend, ML, eval tests | 425 passed (2026-10-28) |
| Playwright e2e, real UI sign-in | 17/17 on the live Cloud Run site (2026-10-27) |
| Fresh clone from GitHub (`scripts/fresh_clone_check.sh`) | passes end to end |
| `docker compose up --build` | healthy; ledger sealed at image build |
| `terraform validate` | passes (Terraform 1.16, google provider 5.45) |
| Cloud-mode code paths | tested with Google clients faked; never run against real GCP |

## Results (all logged in `eval/reports/runs.jsonl`)

| Acceptance | Result | Honest reading |
|---|---|---|
| AC4 forecasting, real HMIS frozen test | LightGBM WAPE 0.871 vs lag-1 naive 1.078, median-of-3 0.959 | Clean win (-19%). Second logged attempt; the first (1.110) lost and is kept. |
| AC6 stock-out replay, synthetic test window, deployed policy (>= 10 units, <= 5 donors) | stock-out weeks 10,774 → 10,244 (-4.9%) | Unmet units +0.41%, fill 67.83% → 67.70%, ~230 transfers/week. Unconstrained run kept: -6.0%, +0.25% unmet, ~570/week, 2.7x the driving. |
| AC6 end to end, demand read from weekly counts (live estimator), same window and events | stock-out weeks 10,774 → 10,584 (-1.8%) | Unmet units -1.06%, fill 67.83% → 68.17%, 4,170 transfers. 303 facilities better, 196 worse; vitamin A syrup worse (417 → 517). `eval/reports/replay_breakdown.json`. |
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
- Homepage data: the latest-stock index is held in memory (built at startup), so
  `/public/district-summary` no longer reads 12k Firestore rows per request (was ~8 s warm,
  now 0.6-0.9 s). Officer redesign (build ef80806): Playwright 15/15 against the Cloud Run URLs.
- Voice notes and national reach (build be546c4): Playwright 16/16 against the Cloud Run URLs,
  including a Hindi voice note transcribed by Chirp 2; 340 backend tests pass.
- Audit fixes (2026-10-26): Pub/Sub publish is awaited, inbound handling runs off the event loop,
  simulator media capped at 20/min, alerts in each contact's language, expired drafts left out of
  the order list, an order lock so proposals can't expire a just-approved order, IVR webhook
  removed (it could never match a facility). 344 backend tests.
- Beds and staff wired (2026-10-26): `BEDS 4/6` and shared-location check-ins (200 m geofence) on
  WhatsApp; `/officer/capacity/{district}` and the briefing's "Beds and staff today" card with
  referral and deputation suggestions from the OR-Tools solvers. Demo mode fills unreported
  facilities with a generated baseline (labelled, never stored). 356 backend tests, 17 e2e.
- Mock-judge fixes (2026-10-26): approval checks the donor's projected stock (approved-since-report
  transfers counted), proposals use it too; failed alerts are retried by approving again; receipt via
  `RECEIVED <code>` or Mark received; YES confirms only the latest card; duplicate message ids ignored;
  media checked by type, size and file signature; quantities like 1,000 read whole, -5 and 10.5 refused
  with a reply; one person counts once in attendance, census older than a day is unknown; ISO state
  codes (no ID collisions); live drafts at least 10 units, at most 5 donors per need (160 to 77);
  state-wide proposals cross district lines; the held-out block is enforced; federated local-only arm
  scaled with training statistics (0.9931). 375 backend tests.
- Second mock-judge pass (2026-10-26): agent takes facility names and beds/staff questions, and
  sends anything else to Gemini function calling (read-only, jurisdiction-checked, numbers guarded),
  checked live; 15 Dhule facilities carry labelled demo stock, so a state-wide run drafts 58
  cross-district transfers live; referrals and deputations approve into signed orders; simulator
  plays voice alerts; backend kept warm (min instances 1) until results. 381 backend tests, 17/17
  e2e live (one intermittent client error right after a deploy, passed on two reruns).
- Third mock-judge pass (2026-10-26): units promised away stay reserved at the donor until `SENT
  <code>`, and units on their way cannot be sent onward; agent's current stock is the latest confirmed
  count; answers need a tool result for every number; deputation role and head count are signed;
  same-day bed corrections win; concurrent proposals leave one plan; a saved report is not saved twice
  when its reply fails; one card shows every item waiting for YES; Resend alerts on the order card;
  demand from each facility's own counts; replay of the deployed policy; two-process federation demo
  served at `/public/federated`; alerts to the contacts registry; voice alerts served for Twilio.
  399 backend tests.
- Fourth review (2026-10-27): a facility's beds, staff or transfers question goes to Gemini, not its
  stock template; a sum or difference of two returned numbers counts as grounded; reported use adds
  back transfers received between counts and averages with the previous reading; approved referrals
  and deputations move patients and staff in today's numbers (no double suggestion), and their
  alerts ask for RECEIVED; voice clips over the store limit go as text only; the public page shows
  the federated model's estimates. 404 backend tests.
- Fifth review (2026-10-27): demand from counts nets transfers out, keeps a day-old anchor and treats
  an empty shelf as censored (shared estimator `ml/forecast/reported_use.py`); a late retry keeps its
  original time; approved referrals and deputations are planned around, reported beds and staff stay
  as reported; approval rechecks the donor's two-week buffer; dispatch and receipt are checked on the
  stored order; new facilities forecast from their own use; agent capacity and orders take a
  facility; voice clips expire after a week (Firestore TTL); end-to-end replay with demand from
  counts (-1.8% stock-out weeks, -1.06% unmet units).
- Limits: backend max 1 instance (in-memory simulator outbox; caps cost), frontend max 2, both scale
  to zero. Budget alert Rs 850/month (alerts only).
- Not configured: Firebase Auth and Twilio (demo sign-in and the simulator stand in), Maps
  (straight-line travel time).


**Render (2026-10-26):** backend suspended; the frontend at https://aushadhinet-frontend.onrender.com (the submitted link)
is the same app against the Cloud Run backend, which allows its origin. 8/8 e2e pass on it.

Serving measured ~312 MB at startup, ~374 MB peak while proposing
transfers (was ~860 MB before the serving footprint was trimmed); Cloud Run is given 2 GiB for headroom. Free instances sleep
when idle, so the first request after a pause takes 30-60s. This runs in local mode: the
sealed ledger, no GCP credentials. AC11 (real GCP services) is still unrun.

## Known limits

- Local state (stock, orders, outbox) is in memory; restarting the backend resets it.
- Agent in local mode is keyword dispatch over the same tools; the Gemini function-calling path is
  cloud-only and untested against the real API.
- Register photos: Gemini reads every line (checked against the real Developer API through the
  simulator UI). Without `GEMINI_API_KEY` (local mode) a photo
  gets a "please type it" reply. Every photo read waits for the nurse's YES.
- Free Gemini tier: 100 embedding calls a minute, so NLEM name matching uses the offline matcher
  (with Indic-script names from `backend/i18n.py`) rather than Gemini embeddings.
- Proposals run on demand (Orders button or agent), not on a schedule.
- One unused variable in `ml/generator/ledger.py` is deliberately left alone (sealed generator).
