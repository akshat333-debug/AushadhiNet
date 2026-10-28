# AushadhiNet — what is done and the decisions behind it

Updated 2026-10-25. Status and numbers: `state.md`. Pending work: `tasklist.md`. Every bug found and
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
| 2026-10-24 | Register photos read by Gemini in the hosted app (every line, always confirmed); finale demo script and Q&A. |
| 2026-10-26 | Audit fixes 1-12; beds (`BEDS 4/6`) and staff check-ins (shared location, geofenced) wired end to end, with referral and deputation suggestions in the officer briefing. |
| 2026-10-25 | Voice notes (Chirp 2), national reach view, 12-slide deck, video re-recorded. |
| 2026-10-25 | Officer redesign: morning briefing (escalate vs move stock), before/after transfer map, urgency-sorted orders, animated how-it-works; homepage load 8 s to instant. |
| 2026-10-24/25 | Deployed on Google Cloud Run with Firestore, BigQuery, Pub/Sub, KMS, Secret Manager and Vertex AI; Gemini adds a guarded note to agent answers. |

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

1. **Full scope (medicines, beds, staff)** because the Track 3 brief names all three. Beds
   (`BEDS 4/6`) and staff check-ins (shared WhatsApp location, geofenced) arrive on the same
   WhatsApp number; the officer briefing shows referral and deputation suggestions from the
   OR-Tools solvers (2026-10-26). Bed counts and posts per facility are IPHS-style norms (the
   national directory has neither); facilities that have not reported show a generated baseline,
   labelled, in demo mode only, and it is never stored.
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
8. **Render first, then Google Cloud Run**: no hackathon credits, so the submission ran on Render.
   On 2026-10-24 the team's own GCP trial was enabled and the same Terraform + Cloud Build scripts
   deployed it (Rs 850/month budget alert, instances scale to zero). On 2026-10-26 the Render backend was suspended; the Render frontend (the submitted link) now calls the Cloud Run backend.
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
15. **Every photo read needs the nurse's YES**, even when Gemini is confident: a model reading a
    photo can be confidently wrong, and a wrong stock count drives a wrong transfer.
16. **Gemini in local mode when a key is present**, falling back to the local provider: the hosted
    demo shows real Google AI without needing GCP billing, and never breaks on a rate limit.
17. **Facts verified against primary sources** before use (HDI 2022-23 facility counts, eVIN study);
    an unverified "29% → 75%" claim was removed.
18. **Gemini explains, rules act** in the agent: tools are chosen by rule and Gemini only adds a short
    note, which is dropped if it brings a new number or mentions approving or sending. Keeps the
    "cannot be talked into an action" guarantee while showing Gemini reasoning over live data.
19. **Designed for the district officer first, with a judge-ready first screen** (2026-10-25). The
    nurse already has the right interface (WhatsApp); the officer needed "what do I do this
    morning", not totals.
20. **Shortages split into "escalate" and "move stock"** instead of one "at risk" count. 729 of 760
    facilities showed as at risk because calcium demand in the real HMIS data jumps ~20x in Dec
    2019 and supply lags. When a drug's district-wide stock is under the solver's 2-week planning
    cover, no facility can spare any, so transfers cannot help: those drugs go to a state supply
    request with a quantity (2 weeks of demand less stock). Kept the real data rather than hiding
    the drugs or moving the snapshot week.
21. **Orders triaged by urgency** (destination's days of cover), names first, bulk "approve the 5
    most urgent" behind a second click; the map shows before/after the drafted transfers.
22. **Latest-stock index kept in memory** on the backend (one instance), updated on every confirmed
    write: the Firestore full read took ~8 s per request.
23. **Voice notes always wait for YES**, like photos, with the transcript quoted on the card; Chirp 2
    detects the language because an English hint dropped "ORS" from a Hindi note.
24. **Several items on one line are split** by the parser: "ओआरएस 50 जिंक 120" used to be saved as
    ORS 120 at full confidence (a silent wrong write).
25. **National reach from the real directory**, not new data: 190,609 facilities in 36 states and UTs
    are listed from the directory, not onboarded; Nashik has the synthetic ledger and 15 Dhule facilities labelled demo stock. The duplicate "Andhra Pradesh Old" rows
    (pre-2014, 98% repeats) are excluded.
26. **Claims scoped to what runs**: the app serves the last-week forecast per facility; LightGBM's 19%
    is the district-level real-HMIS result, and the deck and README now say so.

## Measured results

See `state.md` "Results". Summary: forecasting -19% WAPE vs naive (real HMIS); 26-week replay of the
deployed policy: stock-out weeks -4.9% with ledger demand (unmet +0.41%), -1.8% with demand read from
counts (unmet -1.06%); federation ties local-only; Gemini extraction 98.1% medicine / 100% quantity on
206 synthetic register renders; 423 backend tests, 17/17 e2e on the live site.
