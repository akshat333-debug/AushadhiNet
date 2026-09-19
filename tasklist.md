# AushadhiNet — task list

Deadline 30 Sep 2026. Current state in `state.md`; history in `TASK.md`.

## Before the video and deck

- [ ] **Decide the extraction claim (AC3).** No real accuracy number exists. Either get a Gemini key,
      photograph some real registers, and run `eval/run_extraction_eval.py`, or make no numeric claim.
- [ ] **Deck framing, using `state.md`'s results table:** AC4 is a clean win; AC6 is "fewer
      facility-weeks with nothing on the shelf", not "less shortage"; AC9 is "matches local accuracy
      without pooling raw data", not "federation wins".
- [ ] **Manual run-through of the demo** start to finish before recording (README walkthrough). A
      full-district proposal returns hundreds of drafts; decide how to show it on screen.
- [ ] Methodology and limitations slide (frozen protocol, sealed generator, what is synthetic).

## Cloud deploy (AC11), when GCP credits arrive

- [ ] `terraform apply` in `infra/terraform/state-module` with a real `project_id`.
- [ ] Add secret values: `twilio-auth-token`, `gemini-api-key` (`gcloud secrets versions add`).
- [ ] Enable Firebase Auth; create officer users with `role` and `jurisdiction` custom claims.
- [ ] `gcloud builds submit --config infra/cloudbuild.yaml` (two passes for the Cloud Run URLs).
- [ ] `terraform apply -var backend_url=...` to turn on Pub/Sub push.
- [ ] `AUSHADHI_MODE=cloud python -m backend.runtime seed` to load Nashik into Firestore.
- [ ] Point the Twilio sandbox webhook at `<backend>/webhooks/twilio`; send a real message.
- [ ] Smoke-test the Gemini agent and extraction paths against real APIs (never exercised yet).

## Optional improvements (dev window only, then one logged test run)

- [ ] Cut AC6 transfer volume: minimum transfer size or route batching.
- [ ] Persist local-mode state (e.g. DuckDB) so restarts keep the demo data.
- [ ] Scheduled proposals (Cloud Scheduler → propose endpoint) instead of on-demand only.
- [ ] Wire or remove the unused forecasting modules (Croston/ensemble, calibration, reconciliation).
