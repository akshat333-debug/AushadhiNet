# AushadhiNet — what is done and the decisions behind it

Updated 2026-10-21. Status and numbers: `state.md`. Pending work: `tasklist.md`. Every bug found and
fixed during the build: `docs/build-log.md`.

## Timeline

| Date | Milestone |
|---|---|
| 2026-09-18 | Review-1 research document (v2) and scope fixed: medicines, beds, staff for PHCs. |
| 2026-09-18/19 | Evaluation protocol frozen and synthetic generator sealed before any model was trained. |
| 2026-09-19/20 | Backend, ML, federation, agent, solver, frontend built file by file with tests; real-HMIS forecasting result logged. |
| 2026-09-29 | Repo cleanup; deployed to Render (Blueprint, free tier, local mode). |
| 2026-09-30 | Frontend redesign; 7 languages end to end; live e2e 13/13; demo video (Sarvam voice-over) and pitch deck; submitted. |
| 2026-10-01 | Gemini Developer API path fixed and measured; Indic-script medicine matching; service-worker fix; MIT license. |
| 2026-10-21 | Team Visible named a top-10 finalist, Track 3. Repo cleanup: unused forecasting modules removed. |

## What is built

- **Nurse channel:** WhatsApp (Twilio webhook, or the in-app simulator) for text, photo and voice
  reports in 7 languages (en, hi, mr, bn, ta, te, kn), native scripts and native digits. Unsure reads
  get a one-tap confirmation card; nothing unconfirmed reaches the forecast.
- **Extraction:** text parser plus Gemini for register photos and Chirp for voice (cloud mode),
  normalised against the NLEM medicine list.
- **Forecasting:** LightGBM evaluated on real India HMIS data (WAPE 0.871 vs naive 1.078); the served
  facility-week forecast is lag-1 naive because it won on recent weeks. Stock-out probability per
  facility and medicine.
- **Rebalancing:** Google OR-Tools solver drafts transfers from nearby surplus to at-risk facilities;
  officer approves; orders are HMAC/KMS-signed; both facilities alerted by WhatsApp text and voice.
- **Officer agent:** explains risk and drafts proposals; has no approve or send tool at all;
  jurisdiction-scoped; prompt-injection tested.
- **Federation:** Flower-style federated training with DP-SGD on state-partitioned data (ties local-only).
- **Frontend:** Next.js 15 dashboard with a facility map, facility pages, orders, agent chat,
  WhatsApp simulator, public transparency view; light and dark themes; PWA with offline shell.
- **Infra:** Dockerfiles, docker-compose, Terraform for a per-state GCP project, Cloud Build,
  `render.yaml` for the live demo.
- **Deliverables:** demo video (`docs/pitch/AushadhiNet-demo.mp4`, Drive link in README), pitch deck
  (`docs/pitch/`), README for judges.

## Decisions and why

1. **Full scope (medicines, beds, staff)** because the Track 3 brief names all three.
2. **Frozen evaluation before modelling** (`eval/protocol.lock`), sealed synthetic generator with a
   content hash, and a test that fails if forecasting code imports the generator. Avoids an oracle
   advantage a judge could find.
3. **Headline forecasting number from real HMIS data**, not synthetic; WAPE/MASE, not MAPE. The first
   scored attempt (L2, lost to naive) stays in `eval/reports/runs.jsonl`.
4. **Serve lag-1 naive in the app** because it beat LightGBM on the most recent weeks (team decision).
5. **Every Google service behind a local twin** (`backend/providers/`), so the app runs with zero
   credentials and swaps to Google with `AUSHADHI_MODE=cloud`.
6. **Human in the loop:** the agent structurally cannot approve or send; only an officer can.
7. **Honest framing:** federation "matches local without pooling raw data", not "wins"; the AC6
   replay "rebalances scarcity, adds no supply".
8. **Render instead of GCP for the live demo**: no hackathon credits and GCP billing could not be
   enabled. Cloud deploy is scripted (Terraform + Cloud Build) but not run.
9. **Trimmed serving footprint** (served states, recent-weeks slice) to fit Render's 512 MB.
10. **Gemini via a free AI Studio key** (Developer API): fixed schema (no `additionalProperties`),
    embedding batches of 100, current model `gemini-3.1-flash-lite`.
11. **Indic-script names matched against the app's own localized names**; a near-miss spelling scores
    at most 0.8 so it still needs confirmation (safety over convenience).
12. **Network-first service worker**: cache-first pinned visitors to the old UI after deploys.
13. **Translations written in-house, not certified**: flagged for native-speaker review.
14. **Removed unused forecasters** (Croston, ensemble, TimesFM, BQML ARIMA, calibration,
    reconciliation) on 2026-10-21: built and tested but never called by the app, so they overstated
    what runs. Recoverable from git history.
15. **Facts verified against primary sources** before use (HDI 2022-23 facility counts, eVIN study);
    an unverified "29% → 75%" claim was removed.

## Measured results

See `state.md` "Results". Summary: forecasting -19% WAPE vs naive (real HMIS); stock-out weeks -6.0%
in a 26-week simulation; Gemini extraction 98.1% medicine / 100% quantity on 206 synthetic register
renders; 13/13 e2e on the live site.
