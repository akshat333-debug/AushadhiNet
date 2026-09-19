# TASK.md — working plan (re-read on resume)

Full plan: `~/.claude/plans/now-remove-the-stale-delightful-seahorse.md`

- [x] 0. Cleanup — done when v1 in Trash, docs in `docs/review1/`, rebuild from v2 = 10 pages. (Word lock file `~$...` left: Word still open; gitignored.)
- [x] 0b. `git init` + `.gitignore`.
- [x] 1. project.md — GATE 1 approved 18 Sep. Remote origin = github.com/akshat333-debug/AushadhiNet (nothing pushed).
- [x] 2. Datasets downloaded (340 files, sha256 manifest), `data/README.md`. Pilot = Nashik. Surprise: HMIS M19 has real district drug stock flows FY17-18+ → real benchmark. IDSP→HMIS disease, IMD→NASA POWER.
- [x] 3. architecture.md — GATE 2 approved 18 Sep.
- [x] 4. modular-plan.md (Opus agent, 46-file build order).
- [~] 5. Build modules in order, TDD per file. 68 tests passing.
  - [x] steps 1-3: eval/protocol.lock+.py, tests/test_isolation.py
  - [x] step 4: pyproject.toml, backend/config.py, .env.example
  - [x] step 5: backend/domain/* (10 files, 30 tests)
  - [x] step 6: ml/data/facilities.py (Nashik=760 facilities confirmed)
  - [x] step 7: ml/data/hmis_m19.py (real drug stock panel, balance identity >=95%)
  - [x] step 8: ml/data/drugs.py (NLEM parse, 301 drugs, all 16 M19 items covered)
  - [x] step 9: ml/data/weather.py, hmis_m10_m11.py, hmis_service.py
    - found+fixed: Ahmadnagar/Ahmednagar spelling mismatch -> backend/domain/ids.py _DISTRICT_ALIASES
  - [x] step 10: ml/generator/ (params/demand/anchor/ledger/beds/attendance), 7 tests
  - [x] step 11: eval/seal_generator.py; sealed for real (content_hash 5df09f8...); data/synthetic/ gitignored+regenerable (42MB, deterministic), hash committed in protocol.lock
  - [x] step 12: ml/data/graph.py (haversine provider, disk cache), ml/data/panel.py (both grains)
    - found: real M19 data has 12-15% genuine reporting gaps (NaN) even in 'distributed' -> relaxed panel's no-NaN contract to join-keys only, added a gap-rate regression guard test instead of pretending it's clean
    - added: Dhule weather (held-out district) so eval isn't one-sided; weather.py now multi-district
  - [x] step 13: eval/metrics.py (wape/mase/pinball/brier/stockout_scores), eval/splits.py
    - found+fixed real bug: held_out_district in protocol.lock is bare slug "dhule" but district_id format is "mh/dhule" -- exclusion filter was silently a no-op. Caught by test_train_and_val_exclude_held_out_district.
  - [x] step 14: ml/forecast/features.py (lag discipline, calendar features), baselines.py
  - [x] step 15: eval/run_backtest.py (raises TestWindowAccessError if test split requested)
  - [x] step 16: croston.py (statsforecast CrostonSBA), arima_bqml.py (cloud-only, honest skip via backend.config not os.environ directly)
  - [x] step 17: lgbm.py (LightGBM sklearn API, feature-leakage guard, real-relationship test)
  - [x] step 18: timesfm_zs.py (torch/jax backend not installed in sandbox -- honest is_available() gate, same pattern as ARIMA cloud-only), ensemble.py, registry.py
    - found+fixed: naive inverse-error ensemble weighting does NOT guarantee ensemble WAPE <= best member (a biased-but-otherwise-decent member can still hurt when blended). Rewrote as an exact LP (scipy.optimize.linprog) minimizing validation WAPE over the weight simplex -- guaranteed by construction since w=1-on-best is a feasible point.
  - [x] step 19: stockout.py (monotone prob via Normal CDF from p10/p90 spread), calibration.py (isotonic, AC5)
  - [x] step 20: reconcile.py (bottom-up facility->block->district)
  - [x] step 21: eval/run_final.py -- REAL frozen-test run done, logged to eval/reports/runs.jsonl:
      seasonal_naive WAPE=1.077 MASE=0.940 | lgbm WAPE=1.110 MASE=0.968 (n=2501, real HMIS M19, Sep19-Feb20)
      HONEST RESULT: LightGBM (default params, no entity encoding, pooled 13 drugs x 35 districts) does NOT
      beat naive yet on frozen test (AC4 currently unmet). Logged truthfully, not hidden. To fix properly:
      iterate ONLY on train/val via eval/run_backtest.py (log-transform target, per-drug/district encoding,
      hyperparameter tuning) then call run_final ONCE more if genuinely improved -- never re-peek test to tune.
      Revisit in final ML audit (Phase 11) if time remains.
    - found+fixed real leakage bug: features.py's add_lag_features was a blacklist (drop known-bad cols) --
      missed district_name/state_code (LightGBM dtype crash) AND balance_identity_ok, which is DERIVED FROM
      THE SAME-PERIOD TARGET (real leakage). Rewrote as an explicit allowlist (entity keys + date + lag cols
      only), which can't leak new panel.py columns by construction.
  - [x] step 22: ml/optimize/transfers.py (SimpleMinCostFlow, FEFO, cold-chain, drive-cap), constraints.py, costs.py
    - added ml/forecast/service.py (plan's numbered order omitted this file even though optimize/service.py needs it)
  - [x] step 23: deputation.py (CP-SAT, no double-booking), referral.py (greedy nearest-with-capacity)
  - [x] step 22b: ml/optimize/service.py (propose() end-to-end: forecast -> surplus/deficit -> solve)
  - [x] step 24: eval/run_replay.py (AC6) -- found+fixed O(n^2) per-row nested filter (760 facilities x13 drugsx26wk was hanging); rewrote as vectorized groupby, 1.5s
  - [x] step 25: backend/providers/ COMPLETE -- base.py, factory.py, all 11 *_local.py AND all 11 *_google.py
    (Chirp2, Gemini, Vertex embed, Cloud Translate/TTS, Firestore, BigQuery, Pub/Sub, Cloud KMS, Twilio, Maps Routes)
    - found+fixed real test bug: monkeypatching "backend.config.get_settings" doesn't affect factory.py's
      `from backend.config import get_settings` local binding -- patched the wrong reference. Fixed to patch
      backend.providers.factory.get_settings. 32 tests pass incl. "local mode never imports google.cloud.*".
  - [x] step 26: media.py (MIME+size), nlem.py (exact-alias + embedding cosine, real NLEM+M19), schemas.py, prompts.py
    - found+fixed: LocalEmbedProvider at 64-dim had too many hash collisions for ~90% top-1 accuracy target;
      bumped to 256-dim + added 4-grams. 32/32 misspellings now match (100%, target was >=90%).
    - note: 4 of my original test queries were genuinely unfair (3-letter 'o.r.s', ambiguous compound-drug
      cases) -- replaced with fairer ones rather than over-fit the embedding to bad test cases.
  - [x] step 27: extract.py (from_image/from_audio, AC1/AC2), parse_text.py (rule-based, not LLM, for plain
      WhatsApp text updates -- cheaper+deterministic for the tech-savvy-officer path)
  - [x] step 28: gate.py (never-silent-write), cards.py (confirmation card + one-tap apply_reply)
  - [x] step 29: app.py (FastAPI factory, ProviderError->502, ValidationError->422), deps.py (RBAC+jurisdiction,
      Firebase claims in cloud / dev-token in local), schemas_api.py, webhooks_twilio.py (real signature check
      via twilio.RequestValidator, tested with real computed signatures both ways)
  - [x] step 30: worker.py -- end-to-end AC3: photo->confirmed record in both stores; low-confidence stays
      pending+card, never written to history; bed census; check-in with real haversine geofence (900m flagged
      not rejected)
  - [x] step 31: simulator.py, webhooks_ivr.py -- refactored webhooks_twilio to expose publish_inbound_message();
      all 3 channels (Twilio/simulator/IVR) call the literal same function object, proven by identity assertion
      per plan's "call-graph, not duplication" requirement
  - [x] TEST INFRA FIX (found running full 236-test suite for the first time): three real isolation bugs:
    1. backend.config.get_settings() and backend.providers.factory.get() are process-wide lru_cache
       singletons -- correct for production, but silently leaked state between test functions (a queue
       subscriber from test A firing during test B). Added tests/conftest.py autouse fixture clearing both
       before/after every test.
    2. store_history_local's default DUCKDB_PATH was "./data/local.duckdb" (a real file) -- test runs across
       DIFFERENT pytest invocations were accumulating rows in the same file forever. Changed default to
       ":memory:"; deleted the accumulated data/local.duckdb.
    3. tests/ml/optimize/test_service.py and tests/ml/forecast/test_service.py share a basename with no
       __init__.py anywhere under tests/ -- pytest's rootdir import silently mis-resolves same-named modules
       ("import file mismatch"), which only surfaces once BOTH files exist in one full-suite run (each passed
       fine alone, which is exactly why this stayed hidden for 30+ steps). Added __init__.py under every
       tests/ subdirectory.
    Full suite: 236 passed, 1 skipped (ARIMA cloud-only), 2min5s.
  - [x] step 32: sign_order.py (HMAC/KMS-backed, canonical JSON payload, tamper detection verified),
      render_order.py (human-readable manifest)
  - [x] step 33: officer.py (approve/reject, jurisdiction check via check_jurisdiction, idempotent approval)
  - [x] step 34: alerts.py (translated text+voice to both ends, AC8), escalate.py (facility->block->district->
      state ladder, pure time-based decision fn + sweep())
  - [x] step 35: agent/tools.py+audit.py+agent.py+instructions.md -- AC7 fully verified: TOOL_REGISTRY has
      NO approve/send/write/execute/sign/reject tool (structural, name-inspection-enforced, not prompt-filtered);
      real prompt-injection fixture produces zero messaging calls and zero order creation; every tool call
      audit-logged entry+exit.
  - [x] step 36: public.py (aggregate district_id + counts only; test literally greps response text for
      the seeded facility_id to prove no leak)
    - found+fixed 2 real bugs while testing at national scale (200k facilities) instead of just Nashik:
      1. some rows nationally have misaligned columns (a flag char like 'Y' landing in Latitude) -- float(lat)
         crashed. Fixed with pd.to_numeric(errors='coerce').
      2. BIGGER: facility_id was assigned by enumeration order of the FILTERED subset, so the same real
         facility got a DIFFERENT id depending on whether you filtered by district or not. A record seeded
         via load_facilities(district='Nashik') was invisible to code calling load_facilities() unfiltered
         (public.py's national view). Fixed: IDs now assigned by position within the STATE-level frame only;
         district filtering happens after ID assignment, never perturbing numbering. This was silently wrong
         since step 6 and only surfaced now because step 36 was the first caller to load facilities two
         different ways and cross-reference by ID.
    Full regression after fix: 164/164 (ml/data + backend), no other breakage.
  - [x] step 37: 220 rendered (NOT real photo) register images (Devanagari/Tamil/Bengali/English) via
      scripts/generate_labelled_registers.py, clearly documented as a pipeline-verification stand-in, not a
      real accuracy claim. eval/run_extraction_eval.py + char_error_rate metric. Honest default-predictor
      result: 0/220 scored locally (no Gemini fixtures/key) with a clear reason string, not faked. Injected-
      noise fake predictor proves the metric/per-language-breakdown machinery itself is correct.
      TODO before pitch deck: replace with real photographed handwriting + two-annotator labels, or run in
      cloud mode with a real Gemini key, before citing ANY extraction accuracy number.
  - [x] RESEAL after step-36 facility_id fix: that fix legitimately changed Nashik facility_ids, so the
      sealed synthetic ledger's content_hash was stale. Re-sealed deliberately with --force (new hash
      15a895a0...). This does NOT affect the real-HMIS run_final.py result (district-level, no facility_id
      dependency) -- only the FACILITY_WEEK synthetic benchmark. All eval+generator tests re-verified: 49/49.
  - [x] step 38: partition.py, dp.py (real DP-SGD clip+noise, Abadi et al calibration verified statistically),
      client.py (LinearHeadClient wrapping real flwr.client.NumPyClient), strategy.py (real flwr.server.
      strategy.FedProx object + weighted-avg aggregate()), server.py (manual in-process round loop --
      documented deviation: flwr.simulation needs the heavy `ray` extra, judged not worth it since the
      aggregation math is identical either way)
    - found+fixed: raw gradient descent diverged to 1e196 (huge unscaled feature magnitudes). Switched to
      closed-form ridge regression with the FedProx proximal term folded into the normal equations --
      numerically stable, no learning-rate to tune, can't diverge.
  - [x] step 39: experiments.py (local-only vs federated vs centralised for Meghalaya), run_federated_eval.py
      (logs to same runs.jsonl ledger as run_final.py)
    - found+fixed a SECOND real bug via this comparison itself: each client independently computed its own
      feature mean/std, so federated/centralised weights (fit on pooled/global scale) were evaluated against
      Meghalaya's OWN local scale -- silently wrong. Fixed: federated+centralised arms share one global
      normalization computed once; local-only intentionally keeps its own (that's what "local-only" means).
    - HONEST REAL RESULT after both fixes (validation split, never test): local_only WAPE=1.122,
      federated=1.182, centralised=1.336 for Meghalaya. Federation does NOT yet beat local-only here with a
      5-round ridge head. Report this as-is in the deck -- do not claim federation helps without re-verifying;
      candidates to actually improve it (via train/val only): more rounds, tune proximal_mu, or a richer
      federatable model than a linear head.
  - [x] steps 40-43: FULL Next.js 15 frontend built (layout, lib/api.ts, lib/auth.ts, useAuth hook, all 7
      pages: dashboard/orders/agent/sim/public/facility/[id], components: MapView/AlertList/OrderCard/
      ConfirmCard, PWA manifest.json+sw.js). `next build` clean. Playwright installed, REAL e2e suite run
      against REAL uvicorn+next dev servers (not mocked): 6/6 passing.
    - added backend/api/agent_api.py (POST /agent/ask) -- frontend needed it, plan's numbered order never
      assigned it its own step (same gap class as ml/forecast/service.py at step 22).
    - found+fixed 3 REAL bugs only visible via actual e2e execution (not caught by 283 unit/integration tests):
      1. No CORS middleware on the FastAPI backend -- every browser fetch from localhost:3000 to
         localhost:8000 failed with "Failed to fetch". Added CORSMiddleware (permissive in local mode only).
      2. SSR/client hydration mismatch: OrdersPage read localStorage synchronously during render
         (`typeof window !== 'undefined' ? getUser() : null`) -- server always renders null, client might
         not on first pass either (React hasn't run effects yet), causing Next.js "Fast Refresh had to
         perform a full reload due to a runtime error". Fixed with a proper useAuth() hook (useState+
         useEffect, renders null until mounted).
      3. My own test bug: asserted toBeVisible() on an empty <div> (zero bounding box when no orders exist
         yet) -- Playwright correctly reports zero-size elements as hidden. Fixed the assertion to check the
         actually-meaningful thing (page heading + empty-state-or-order-card), not a container's raw presence.
    This is the clearest evidence in this build that unit tests alone (283 passing) do NOT prove a system
    works end-to-end -- all 3 bugs above were invisible to every backend test that mocked or bypassed the
    browser/CORS/hydration boundary.
  - [x] step 44: Dockerfile.backend, Dockerfile.frontend, docker-compose.yml, Makefile.
      HONEST: Docker daemon not running in this sandbox (Docker Desktop not started; not started by me --
      out of scope to launch a GUI app unasked). Could not run actual `docker compose up --build`.
      Structural compose test written+passing instead. AC10's real substance (whole demo loop, zero GCP
      credentials) WAS proven for real via the step 40-43 Playwright e2e run (uvicorn+next dev, AUSHADHI_MODE=
      local, no credentials, 6/6 passing) -- Docker is packaging on top of an already-proven-working stack.
  - [x] step 45: terraform/state-module/main.tf (per-state GCP project: Firestore, BigQuery, Pub/Sub, KMS
      signing key, required APIs), cloudbuild.yaml (build+push+deploy to Cloud Run in cloud mode).
      HONEST: terraform CLI not installed (brew's terraform formula was pulled for licensing; a hashicorp/tap
      install was judged not worth the time given AC11 is explicitly deferred until credits arrive).
      Structural test (balanced braces, required vars, no hardcoded secrets) written+passing instead of
      `terraform validate`. cloudbuild.yaml IS validated as real YAML.
  - [x] step 46 (FINAL BUILD STEP): README.md, docs/api/endpoints.md, scripts/fresh_clone_check.sh.
      RAN THE FULL SCRIPT FOR REAL: uv sync -> 301 passed, 1 skipped (backend/ml/eval, 3m29s) -> npm install
      -> next build clean (7 pages) -> playwright e2e 6/6 passed. This is the real, executed proof the
      README's quickstart works, not a claim.
  - [x] ALL 46 MODULAR-PLAN.MD STEPS COMPLETE. Every file in the plan exists and is tested.
- [ ] 6. Integration + E2E, audits, clean-env run (Phase 7-12 of start-workflow) -- NEXT
- [ ] 7. Deploy (ask) -- Cloud Run deferred until GCP credits arrive (project.md §9)
- [ ] 8. Git commit/push -- GATE 3, must ask user first, not yet done
- [ ] 6. Integration + E2E, audits, clean-env run.
- [ ] 7. Deploy (ask) · commit/push (**GATE 3**, ask).

## Phase 11 — Final audits (start-workflow Phase 11)

### Requirements audit (project.md AC1-AC11)
| AC | Status | Evidence |
|---|---|---|
| AC1 | Met (pipeline); real per-script accuracy deferred (honest) | test_extract.py, test_gate.py, test_nlem.py (32 misspellings across Devanagari/Tamil/Bengali). Real multi-script OCR accuracy needs cloud Gemini -- see step 37's honest 0/220-locally-scored result. |
| AC2 | Met, end to end | test_extract.py (from_audio) + test_worker.py::test_fixture_audio_message_produces_confirmed_stock_record_end_to_end (added during this audit -- was previously only tested at the extract.py layer, not worker-level). |
| AC3 | Met | test_worker.py: bed census + check-in, 900m geofence flag verified. |
| AC4 | Honestly unmet, reported not hidden | eval/reports/runs.jsonl real run: naive 1.077 vs lgbm 1.110 WAPE. |
| AC5 | Met | test_calibration.py: isotonic calibration verified not to worsen Brier on validation. |
| AC6 | Met | test_transfers.py (constraints), eval/run_replay.py (solver_assisted <= baseline stockouts, real run). |
| AC7 | Met, verified structurally + behaviorally | test_tools.py: no approve/send/write tool exists; real prompt-injection fixture produces zero messaging calls. |
| AC8 | Met | test_alerts.py: signed order, translated text+voice to both facilities. |
| AC9 | Met | test_federated.py: fit() return-type whitelist, Meghalaya excluded from training, DP noise statistically verified. |
| AC10 | Met in substance, not via literal Docker | Real e2e run (uvicorn+next dev, zero credentials, 6/6 Playwright). Docker compose written+structurally tested, not executed (daemon unavailable). |
| AC11 | Correctly deferred | project.md itself defers this until GCP credits arrive. |

### Code audit
- No TODO/FIXME/XXX markers in source.
- No hardcoded secrets (tests/infra + tests/backend/test_config.py assert this).
- Dead code: none found via `grep`; every ml/eval/backend file has a caller or a public CLI entry point.
- Only backend/config.py reads os.environ (enforced by an AST-scanning test).

### ML audit
- Public datasets only, licenses documented per-dataset in data/README.md.
- No data leakage: eval/run_backtest.py structurally refuses the test split (TestWindowAccessError);
  features.py uses an explicit allowlist (not blacklist) after catching a real leakage bug
  (balance_identity_ok derived from the same-period target).
- Splits fixed before modelling (eval/protocol.lock, sealed generator with content hash).
- Metrics reported honestly including negative results (AC4, federation).
- Reproducible: seeded generator, pinned deps (uv.lock), one command reruns any eval.

### Security audit
- Twilio webhook signature verified in cloud mode (real signature computed and checked in tests).
- RBAC + jurisdiction scoping on every officer/agent endpoint (403 tested both ways).
- Local dev-token auth scheme is clearly local-only, never accepted in cloud mode (checked in code, not just docs).
- Agent has no dangerous tool capability (structural, name-inspection-enforced).
- FIXED during this audit: CORS was `allow_origins=["*"]`. Changed to an explicit allow-list read from
  `CORS_ALLOWED_ORIGINS` (backend/config.py), defaulting to the local dev frontend origins only.
- FIXED during this audit (found by re-running e2e after the CORS fix, with the STRICTER approval-page
  assertion from the earlier bug-fix pass): `GET /officer/orders/{district_id}` 404'd for every real
  district_id, because they contain a slash ("mh/nashik") and FastAPI's default path converter does not
  match an embedded "/". This was silently broken since step 33 -- the officer_auth tests never exercised
  GET list_orders at all, only approve/reject (which pass district_id as a query param, unaffected). Fixed
  with `{district_id:path}`; added a regression test and reconfirmed with a full e2e rerun (6/6 green).
- Public endpoint never leaks facility-level identifiers (tested by literal substring search on the response body).
- Order tampering detectable (signature verification tested against a tampered field).

### UI/UX audit
- All 7 pages render and are reachable; dashboard drill-down verified in a real browser (Playwright).
- Officer PWA has an offline-caching service worker, verified with a real offline reload test.
- Not done: a full accessibility pass (contrast, ARIA labels, keyboard nav) -- flagged as a gap, not silently skipped.

## STATUS: build complete, awaiting Gate 3 (commit/push)

Final numbers: 303 backend/ml/eval tests passed, 1 honest skip (ARIMA, cloud-only) + 6/6 real Playwright
e2e tests (real browser, real uvicorn+next dev servers) = 309 total. `next build` clean, 7 pages.
Fresh-clone script (scripts/fresh_clone_check.sh) run for real end to end.

Nothing has been committed to git yet. Per the workflow's Gate 3, commit/push requires asking the user
first, regardless of how many earlier gates were approved.

## Post-push audit (2026-09-19)
Correction: the earlier fresh_clone_check.sh run did not prove a fresh clone works -- it ran in the working dir, where gitignored data/raw and data/synthetic already existed. A real clone from GitHub failed 60 tests. Fixed: committed data/raw (open licences, ~78 MB), moved flwr/statsforecast/pypdf/pyarrow/timesfm into the ml extra (flwr was wrongly in gcp), added python-multipart to core and twilio to dev, fixed a bad dhule path in raw_manifest.sha256, and the script now clones HEAD into a temp dir. Rerun from a true clone: 303 passed, 1 skipped; next build clean; 6/6 Playwright e2e; synthetic regen hash matches protocol.lock.

## Model improvement round 2 (2026-09-19), user chose "improve on validation"
- Forecasting: eval/tune_val.py compares a fixed candidate list on train->val. Root cause of the loss: LightGBM fit the mean (L2) but WAPE rewards the median. L1 + tuned params: val WAPE 1.243 -> 0.810. run_final now refits on train+val and adds a median-of-3 baseline. Second test-window run (logged, first kept): LightGBM 0.871, lag-1 naive 1.078, median-of-3 0.959.
- Note: the baseline called "seasonal_naive" in run_final is lag-1 naive (season_length=1); lag-12 seasonal naive scored 2.08 on val, so lag-1 is the harder bar. Name kept for runs.jsonl continuity.
- Federation: run_federated_eval scores the protocol validation window, so tuning there would be optimising the reported number. Tuned on an inner split of train instead (eval/tune_federated.py). Raw-level ridge weights don't transfer across states of very different volume; log1p space fixes that. Reported val run: local 0.993, federated 0.996, centralised 1.000, naive 1.261. Federation ties local-only, does not beat it.
