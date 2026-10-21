# Hackathon details

What we know about the event, from the brief and organiser announcements. Updated 2026-10-21.

## Event

- **Name:** Build with AI: Code for Communities 2.0 (Second Edition), run by Google; submissions on the
  Hack2Skill (H2S) platform.
- **Our track:** Track 3, **Smart Health & Supply Chain Resilience** (Problem Statement 03). The
  brief covers last-mile health resources: medicines, beds and staff at primary health centres.
- **Other tracks:** 1 AI for Digital Public Infrastructure & Governance; 2 Clean Air & Climate
  Resilience; 4 AgriN & Regenerative Agricultural Intelligence; 5 Cyclone Impact & Infrastructure
  Vulnerability Forecaster.
- **Team:** Visible.
- **Contact for queries:** hdattani@google.com (from the finalist announcement).

## Timeline

| Date | Event |
|---|---|
| 30 Sep 2026 | Submission deadline (met). |
| Oct 2026 | Finalists announced: **Visible is in the Track 3 top 10.** |
| 26-29 Oct 2026 | Virtual finale for Tracks 1-4; each team is contacted separately with its date and time. |
| 30 Oct 2026 | Winners for all five tracks announced. |

## How submissions were judged

The finalist announcement says evaluation covered: **working prototype, use of Google AI, track fit,
impact, deployment readiness, and demo reviews.** The Review-1 planning assumed AI execution carried
about 25% of the score (see `docs/review1/`).

## What we submitted

| Field | Value |
|---|---|
| GitHub (public) | https://github.com/akshat333-debug/AushadhiNet |
| Demo video | https://drive.google.com/file/d/1hv58NXTXzYdrw2FjT-09dVwV-RGRDBeq/view?usp=sharing |
| Deck (PDF, under 5 MB) | `docs/pitch/AushadhiNet-pitch.pdf` |
| Working prototype | https://aushadhinet-frontend.onrender.com |
| Description | 981-character summary (see the README "How AushadhiNet solves it" section) |

## Constraints we hit

- No GCP credits from the organisers; GCP billing could not be enabled on our project, so the live
  demo runs on Render in local mode.
- Free Gemini tier rate limits (100 embedding calls a minute; occasional 429/503 on generation).

## Unknown, to confirm

- Finale slot length, and whether the demo is live or pre-recorded.
- Finale judging criteria and weights (assume the same six as above).
