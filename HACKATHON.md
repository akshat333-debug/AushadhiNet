# Hackathon details

What we know about the event, from the brief and organiser announcements. Updated 2026-10-25.

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
| 1-15 Oct 2026 | Prototype evaluation (event page). |
| 16 Oct 2026 | Top-20 shortlist (event page). |
| Oct 2026 | Finalists announced: **Visible is in the Track 3 top 10.** |
| 26-29 Oct 2026 | Virtual finale for Tracks 1-4; each team is contacted separately with its date and time (finalist email). |
| 30 Oct 2026 | Winners for all five tracks announced. |
| TBA | In-person demo day: winning teams present to industry experts (event page). |

The event page still lists the Virtual Demo Day as 23 Oct; the finalist email (newer, sent to finalists)
says 26-29 Oct. We follow the email; the slot is on the Hack2Skill team dashboard.

## How submissions are judged

From the event brief, by weight:

| Weight | Criterion | Judges ask |
|---|---|---|
| 25% | AI/Technical Execution | Is Google AI doing meaningful work? Does the prototype work end to end? |
| 20% | Problem-Solution Fit | Does it directly address the stated challenge? |
| 20% | Depth & Reach Across India | Can it scale from one city or state to communities across India? |
| 20% | Deployability & Scalability | Could a ministry or several states pilot it within weeks? |
| 15% | Impact Potential | How many people, across how many states, how meaningfully? |

Submission package: public repo, 3-5 minute demo video, **10-12 slide** deck (problem, solution, AI
approach, who it serves, why it is deployable, how it scales across India), a 2-3 line description,
and a live link. Google AI is mandatory. Rule 04: design for cross-border applicability (BRICS).

## What we submitted

| Field | Value |
|---|---|
| GitHub (public) | https://github.com/akshat333-debug/AushadhiNet |
| Demo video | https://drive.google.com/file/d/1hv58NXTXzYdrw2FjT-09dVwV-RGRDBeq/view?usp=sharing |
| Deck (PDF, under 5 MB) | `docs/pitch/AushadhiNet-pitch.pdf` |
| Working prototype | https://aushadhinet-frontend.onrender.com (as submitted); now also on Google Cloud Run: https://aushadhinet-frontend-449585498230.asia-south1.run.app |
| Description | 981-character summary (see the README "How AushadhiNet solves it" section) |

## Constraints we hit

- No GCP credits from the organisers. On 2026-10-24 the team's own GCP free trial ($300 credit)
  was enabled; the app now runs on Cloud Run with Firestore, BigQuery, Pub/Sub, KMS and Vertex AI
  (project `aushadhinet`, budget alert at Rs 850/month). Render stays as a backup.
- Free Gemini tier rate limits (100 embedding calls a minute; occasional 429/503 on generation).

## Unknown, to confirm

- Finale slot date and length, and whether the demo is live or pre-recorded.
- In-person demo day date and venue.
- Finale judging criteria and weights (assume the same six as above).
