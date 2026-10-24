# AushadhiNet — task list

Finale (Track 3, virtual): between 26 and 29 Oct 2026; winners announced 30 Oct. Details in
`HACKATHON.md`. Current state in `state.md`; what is done and why in `PROGRESS.md`.

## Finale prep (highest value first)

- [x] **Gemini reads register photos in the deployed app** (code done 2026-10-24): camera button in
      the WhatsApp simulator, every line read, always confirmed by the nurse, local fallback on 429/503.
- [x] **Deployed on Google Cloud** (2026-10-24): Cloud Run + Firestore + BigQuery + Pub/Sub + KMS +
      Secret Manager + Vertex AI, Terraform-provisioned; 14/14 e2e on the Cloud Run URLs.
- [ ] Finale day: `--min-instances=1` on the backend during the slot, back to 0 after.
- [ ] Optional: `GEMINI_API_KEY` on Render too, so the backup reads photos.
- [ ] Gemini for the officer agent's answers (still keyword dispatch locally).
- [ ] **Real register photos (needs the team):** 15-50 phone photos of handwritten stock lists
      (Hindi/Marathi), no personal data, with a written answer key. Run
      `eval/run_extraction_eval.py`'s `evaluate_gemini` on them for the first real-photo number.
- [ ] **Finale format:** wait for the organisers' email (slot length, live vs recorded demo).
- [x] **Live demo script** and **Q&A sheet**: `docs/finale/` (2026-10-24).
- [ ] Rehearse the demo twice against the Cloud Run site; open it 2 minutes before the slot.
- [ ] **Deck refresh:** extraction result (synthetic, labelled), live Gemini slide, rollout and cost.
- [ ] Native Marathi and Hindi speakers review the translations.

## Security and cost

- [ ] After the finale: delete the GCP project (`gcloud projects delete aushadhinet`) or close the
      billing account, so nothing can bill the card.

- [ ] Rotate the Render, Sarvam and Gemini API keys (all were pasted in chat).

## Cloud deploy (AC11): done for the demo; remaining for a real rollout

- [x] `terraform apply` in `infra/terraform/state-module` with a real `project_id`.
- [x] Add the `gemini-api-key` secret value (`twilio-auth-token` stays empty until a Twilio account exists).
- [ ] Enable Firebase Auth; create officer users with `role` and `jurisdiction` custom claims.
- [x] `gcloud builds submit --config infra/cloudbuild.yaml` (two passes for the Cloud Run URLs).
- [x] `terraform apply -var backend_url=...` to turn on Pub/Sub push.
- [x] `AUSHADHI_MODE=cloud python -m backend.runtime seed` to load Nashik into Firestore.
- [ ] Point the Twilio sandbox webhook at `<backend>/webhooks/twilio`; send a real message.

## Optional improvements

- [ ] Persist local-mode state (e.g. DuckDB) so restarts keep the demo data.
- [ ] Cut AC6 transfer volume: minimum transfer size or route batching.
- [ ] Scheduled proposals (Cloud Scheduler → propose endpoint) instead of on-demand only.
- [ ] Fix the eval render font so Devanagari images show the Latin batch prefix.
