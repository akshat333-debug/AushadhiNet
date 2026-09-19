# AushadhiNet — project.md

Source of truth for requirements. Design rationale: `docs/review1/AushadhiNet_Review1_Document_v2.docx`.
Hackathon: Build with AI: Code for Communities (Second Edition), Problem Statement 03 — Smart Health & Supply Chain Resilience. Submission deadline **30 Sep 2026**.

## 1. Problem statement
India's public health supply chain is digitised at the warehouse (DVDMS/e-Aushadhi, eVIN) but thin at the point of care. Across 1,69,615 sub-centres and 31,882 PHCs (Health Dynamics of India 2022-23), stock is often recorded on paper, entered late or not at all, and bed occupancy and staff attendance are not visible alongside stock. Stock-outs are discovered when a patient is turned away while a neighbouring facility holds surplus that expires. No system converts last-mile visibility into cross-facility action, and any national system must respect state ownership of health data.

## 2. Objective
A federated, Google-AI-powered platform that gives real-time visibility of **medicines, beds and medical personnel** across the PHC network, forecasts shortages 2–6 weeks ahead, and turns forecasts into officer-approved redistribution actions, while letting states share models without sharing raw data.

## 3. Proposed solution (one line)
A nurse reports stock, beds and staff presence by WhatsApp voice or photo in any Indian language; Gemini and Chirp structure it; forecasting models predict shortages; OR-Tools proposes transfers, deputations and referrals; a district officer approves them in chat; alerts and signed orders go out automatically.

## 4. Target users and roles
| Role | Channel | Can do |
|---|---|---|
| Facility reporter (ANM, pharmacist, MO) | WhatsApp (Twilio) / IVR / web simulator | Report stock, bed census, check-in; confirm low-confidence fields; receive transfer alerts |
| Block / district officer | Officer PWA + chat agent | View dashboard, ask agent, approve or reject orders, see escalations |
| State admin | Officer PWA | State-wide view, onboarding, federation participation |
| Public | Transparency page | Aggregate district stock-out days only (no facility-level identifiers beyond public registry) |

## 5. Functional requirements
- **FR1 Capture:** WhatsApp voice note, register photo, text; bed census message; geo-tagged staff check-in; IVR (Dialogflow CX) for feature phones; web WhatsApp simulator for demo.
- **FR2 Extraction:** Chirp 2 transcription; Gemini schema-constrained extraction with per-field confidence; NLEM drug normalisation via embeddings; fields below threshold trigger one-tap confirmation, never silent write.
- **FR3 Storage:** live state (Firestore) and history (BigQuery); open, versioned ingestion contract; adapters for DVDMS export and HMIS.
- **FR4 Forecasting:** facility × drug × week consumption and stock-out probability at 2/4/6 weeks; bed-occupancy and staffing-gap forecasts; hierarchical reconciliation; anomaly flags.
- **FR5 Optimisation:** min-cost-flow drug transfers (drive time, cold chain, buffers, FEFO, expiry); staff deputation; patient referral to free beds.
- **FR6 Agent:** Gemini function-calling agent (ADK) answering officer questions and drafting orders; read-only tools plus approval-gated write; every call audit-logged.
- **FR7 Action:** signed transfer orders with batch manifest; local-language WhatsApp and TTS alerts; route plan (Maps Routes); escalation ladder facility → block → district → state; public aggregate view.
- **FR8 Federation:** per-state data plane; Flower server; FedProx + DP-SGD; comparison of local-only vs federated vs centralised.
- **FR9 Dashboard:** map-first national → state → district → facility drill-down; alerts; order queue.
- **FR10 Multilingual:** Marathi (pilot district), Hindi and English end to end in the demo; Tamil and Bengali covered in the extraction evaluation set; other languages by configuration.

## 6. Non-functional requirements
- Works on a basic phone; offline-tolerant officer PWA.
- Runs fully offline for demo and tests (emulators + local fallbacks), same code path as cloud.
- State data sovereignty: raw facility rows never leave a state's data plane in federation.
- Human-in-the-loop: no transfer, deputation or referral executes without officer approval.
- Latency: capture-to-record p95 under 30 s (excluding human confirmation).
- Security: Twilio signature validation, role-based auth, secrets never in repo, upload type/size limits, audit log.
- Reproducibility: seeded generator, pinned dependencies, `docker compose up` runs the full loop.

## 7. Inputs and outputs
- **Inputs:** WhatsApp media/text, IVR audio, check-in location, public datasets (§10), officer chat.
- **Outputs:** structured stock/bed/staff records, forecasts with probabilities, draft and signed orders, alerts, dashboards, evaluation reports.

## 8. Core workflow (demo path)
1. ANM sends register photo in Hindi via WhatsApp.
2. Gemini extracts rows; one low-confidence expiry date triggers a confirmation card; ANM taps confirm.
3. Record lands in live state + history.
4. Forecast flags ORS stock-out probability 0.8 at 4 weeks for PHC A.
5. Solver proposes transfer of N units from PHC B (surplus, expiring sooner) within 40 min drive.
6. Officer asks agent "why is PHC A at risk and what do you suggest?"; agent explains and shows the draft order; officer approves.
7. Signed order + WhatsApp/voice alerts sent to both in-charges; dashboard updates; escalation timer starts.

## 9. Constraints and assumptions
- GCP project not yet provisioned: all cloud identifiers are placeholders in `.env` (`GCP_PROJECT=REPLACE_ME`); each Google service has a local fallback behind one factory.
- WhatsApp through Twilio sandbox; Meta Cloud API later by adapter swap.
- Facility-level stock ledgers are not public; synthetic ledger used and labelled as such.
- Federation is a working protocol on state-partitioned data, not a live multi-government deployment.
- Staff check-in is a visibility aid, not a replacement for biometric attendance.

## 10. Dataset decision — **YES** (sourced; details and licenses in `data/README.md`)
Pilot district: **Nashik, Maharashtra**. Federation clients: Maharashtra, Haryana, Assam, Meghalaya (data-poor).
| Dataset | Use | License |
|---|---|---|
| HMIS monthly district reports FY2013-14 → FY2019-20, 4 states (336 files) | Demand drivers; **real drug stock flows (M19, FY2017-18+)**; disease signals (M10/M11) | NDSAP / GODL-India |
| All India Health Centres Directory (geocoded, 2016) | Facility network, coordinates | NDSAP / GODL-India |
| NLEM 2022 (PDF) | Drug master list | Government publication (facts only) |
| NASA POWER daily weather | Weather features (replaces IMD) | Open |
| Synthetic ledger (stock, beds, attendance; facility × day) | Facility-level forecasting, optimiser, FL | Ours |
| Labelled register images (≥200) | Extraction evaluation | Ours |

Rule: if any license is unclear, swap the source before use. Record source, license, version and download date in `data/README.md`.

## 11. Training decision — **YES**
- LightGBM global forecaster (Vertex AI custom training; local sklearn-API fallback).
- Croston/SBA for intermittent series; seasonal naive, moving average and ARIMA_PLUS baselines.
- TimesFM zero-shot (no training) as ensemble member.
- Federated training of the forecaster across states (Flower, FedProx, DP).
- Gemini, Chirp, Translation, TTS: pretrained APIs, no training.

### Evaluation protocol (frozen before any model code)
- **Real benchmark (monthly, district × drug, HMIS M19 "Stock Distributed")**: train Apr 2017 → Feb 2019, validation Mar → Aug 2019, **frozen test Sep 2019 → Feb 2020** (Mar 2020 excluded: COVID). Held-out district: Nashik's neighbour **Dhule** is never trained on. Held-out state for FL: **Meghalaya**.
- **Synthetic benchmark (weekly, facility × drug)**: last 26 weeks frozen test; one held-out block.
- Metrics: WAPE, MASE, pinball loss; stock-out recall/precision at 4 weeks, Brier score; replay stock-out days and expired units; extraction field exact-match and CER; latency p50/p95.
- Real-HMIS and synthetic results in separate tables; headline from real HMIS.
- Generator sealed: content hash + seed committed; forecasting code may not import it (enforced by a test).

## 12. Technology requirements (proposed — confirm at Gate 2)
- Backend: Python 3.12, FastAPI, Cloud Run.
- Frontend: Next.js + TypeScript, Google Maps JS API, PWA.
- Data: Firestore (emulator locally), BigQuery (DuckDB locally) behind repository interfaces; Pub/Sub (in-process queue locally).
- AI: `google-genai` (Gemini), Speech-to-Text v2 Chirp 2, Cloud Translation, Cloud TTS, Vertex AI embeddings/Vector Search (local FAISS/numpy fallback), TimesFM, LightGBM, OR-Tools, Flower, Google ADK.
- Messaging: Twilio WhatsApp sandbox.
- Infra: Docker Compose (local), Terraform (per-state module), Cloud Build.
- Tests: pytest, Playwright.

## 13. Expected architecture
Five layers per doc v2 Figure 2: Capture → Ingestion/Extraction → Intelligence → Federation → Action, with a cross-cutting security/interoperability layer. Flow: Input (WhatsApp/IVR/PWA) → FastAPI webhooks → extraction (Gemini/Chirp) → stores → forecasting/solver → agent/officer approval → action (alerts, orders) → dashboard.

## 14. Acceptance criteria
- **AC1** Photo of a handwritten register in Hindi/Tamil/Bengali yields structured rows; fields under threshold always produce a confirmation card (test with fixtures).
- **AC2** Voice note in Hindi yields a correct stock update end to end.
- **AC3** Bed census and staff check-in messages update live state; check-in outside the facility geofence is flagged.
- **AC4** Forecaster beats seasonal-naive WAPE on the real-HMIS frozen test window (reported honestly either way).
- **AC5** Stock-out probability is calibrated (Brier score reported; reliability plot).
- **AC6** Solver returns feasible orders respecting all constraints; replay reduces stock-out days versus the monthly-indent baseline on the synthetic test window.
- **AC7** Agent answers the demo questions using tools only and cannot execute an order without approval (test).
- **AC8** Approved order produces signed document + alerts in the reporter's language.
- **AC9** Federation run shows the data-poor-state result vs local-only and centralised, with raw data never crossing client boundaries (test).
- **AC10** `docker compose up` runs the whole demo path with no GCP credentials.
- **AC11** Deployed on Cloud Run with a public link (after credits arrive).

## 15. Definition of Done
All ACs pass or are honestly reported; audits (requirements, code, ML, UI, security) done; README with setup/run/test/deploy; and the 5 submission artefacts ready: public GitHub repo, 3–5 min demo video, 10–12 slide deck, 2–3 line description, deployed link.
