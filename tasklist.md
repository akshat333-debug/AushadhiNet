# AushadhiNet — task list

Finale (Track 3, virtual): between 26 and 29 Oct 2026; winners announced 30 Oct. Details in
`HACKATHON.md`. Current state in `state.md`; what is done and why in `PROGRESS.md`.

## Finale prep (highest value first)

- [x] **Gemini reads register photos in the deployed app** (code done 2026-10-24): camera button in
      the WhatsApp simulator, every line read, always confirmed by the nurse, local fallback on 429/503.
- [x] **Deployed on Google Cloud** (2026-10-24): Cloud Run + Firestore + BigQuery + Pub/Sub + KMS +
      Secret Manager + Vertex AI, Terraform-provisioned; 14/14 e2e on the Cloud Run URLs.
- [x] Backend warm (`--min-instances=1`) from 2026-10-26 for the judging window.
- [ ] **After results (30 Oct): set it back to 0** (`gcloud run services update aushadhinet-backend --min-instances=0 --region asia-south1 --project aushadhinet`), about Rs 5 an hour until then.
- [ ] **After results (30 Oct): remove both Render keep-awake pings** (reliability aid for judging, not an uptime guarantee):
  - Cloud Scheduler job (every 5 min; free: 1 of the billing account's 3 free jobs):
    `gcloud scheduler jobs delete keep-render-warm --location asia-south1 --project aushadhinet`
  - GitHub Actions workflow (every 10 min, often delayed): `git rm .github/workflows/keep-render-warm.yml`, commit, push.
- [x] Render backend suspended (2026-10-26); the Render frontend (submitted link) calls the Cloud Run backend. 8/8 e2e on it.
- [x] Gemini adds a guarded plain-language note to agent answers on Cloud Run (2026-10-25); the tools still decide every fact and action.
- [ ] **Real register photos (needs the team):** 15-50 phone photos of handwritten stock lists
      (Hindi/Marathi), no personal data, with a written answer key. Run
      `eval/run_extraction_eval.py`'s `evaluate_gemini` on them for the first real-photo number.
- [ ] **Finale format:** wait for the organisers' email (slot length, live vs recorded demo).
- [x] **Live demo script** and **Q&A sheet**: `docs/finale/` (2026-10-24).
- [ ] Rehearse the demo twice against the Cloud Run site; open it 2 minutes before the slot.
- [x] **Deck refresh** (2026-10-25): Cloud Run link, photo reading, extraction slide (synthetic, labelled), rollout and cost slide; video re-recorded on Cloud Run.
- [x] **Officer redesign** (2026-10-25): morning briefing (escalate vs move stock), before/after
      transfer map, urgency-sorted orders with bulk approve, animated how-it-works.
- [x] **Voice notes** (2026-10-25): record in the simulator, Chirp 2 transcribes (language detected),
      confirmed by the nurse; live e2e passes against Cloud Run.
- [x] **National reach** (2026-10-25): every state in the MoHFW directory on the Public view and region browser.
- [x] **Deck to 12 slides** covering every topic in the brief; **video re-recorded** (3:22) on the new flow.
- [x] **Beds and staff wired** (2026-10-26): WhatsApp `BEDS 4/6` and location check-ins; briefing card with referral and deputation suggestions; deck, README and demo script updated. The 3:22 video predates it (medicines only).
- [ ] **Re-upload the video** (`docs/pitch/AushadhiNet-demo.mp4`) as a new version of the same Drive file
      (Drive: File > Manage versions), so the submitted link shows the new one.
- [ ] Native speakers review the translations (all 6 Indian languages; new strings added 2026-10-25).

## Security and cost

- [ ] After the finale: delete the GCP project (`gcloud projects delete aushadhinet`) or close the
      billing account, so nothing can bill the card.

- [ ] Rotate the Render and Sarvam API keys (pasted in chat). The old Gemini key is already invalid; Cloud Run uses the one in Secret Manager.

## Cloud deploy (AC11): done for the demo; remaining for a real rollout

- [x] `terraform apply` in `infra/terraform/state-module` with a real `project_id`.
- [x] Add the `gemini-api-key` secret value (`twilio-auth-token` stays empty until a Twilio account exists).
- [ ] Enable Firebase Auth; create officer users with `role` and `jurisdiction` custom claims.
- [x] `gcloud builds submit --config infra/cloudbuild.yaml` (two passes for the Cloud Run URLs).
- [x] `terraform apply -var backend_url=...` to turn on Pub/Sub push.
- [x] `AUSHADHI_MODE=cloud python -m backend.runtime seed` to load Nashik into Firestore.
- [ ] Point the Twilio sandbox webhook at `<backend>/webhooks/twilio`; send a real message.

## Optional improvements

- [x] ~~Persist local-mode state~~: superseded; the Cloud Run deployment keeps state in Firestore .
- [ ] Cut AC6 transfer volume: minimum transfer size or route batching. Deferred: it changes a frozen, logged result and needs a new scored run, not a finale-week edit.
- [ ] Scheduled proposals (Cloud Scheduler → propose endpoint). Deferred until Firebase Auth exists: the job needs a real service identity, not a demo token.
- [ ] Fix the eval render font so Devanagari images show the Latin batch prefix. Deferred: regenerating the eval set means re-scoring all 220 images; real photos matter more.
