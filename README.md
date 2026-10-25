# Clear House

Group hackathon effort by Pierce, Umair, Phone, and Ryan for **GDG Build with AI x Hacktoberfest 2026** (Virginia Tech, Oct 24-25, 2026). Theme: **AI for Housing**.

## Problem

Finding safe, affordable housing is hard for low-income people, especially students and families in crisis. Listings are scattered, fake and scam listings are common, leases are full of confusing legal language, and emergency help is hard to find when you need it fast.

## Solution

**Clear House** is an AI housing assistant for **Northern Virginia**, powered by Gemma 4, that helps people:

- **Find affordable housing.** Matches a person's budget, location and accessibility needs to manually verified affordable and low-income housing listings.
- **Find emergency help.** Points people to verified shelters and emergency housing resources, with urgent cases shown first.
- **Ask Gemma, live.** A chat that streams its answer as Gemma writes it, grounded in the verified list. "Near my office at …" questions are answered instantly with distances and drive/transit times (Google Places + Routes), no AI needed. If Gemma is unavailable, the chat still lists matching checked resources.
- **See it on a map.** Reviewed homes on Google Maps (Leaflet fallback), plus homes within walking distance of a grocery store, pharmacy or transit stop.

To avoid made-up information, the assistant only recommends places from our hand-verified resource list (`data/resources.json`). Answers are informational and are not legal advice.

## Tech used

- **Gemma 4** (`gemma-4-26b-a4b-it`) through the Gemini API, for understanding requests, writing grounded answers (streamed live), and checking whether listings are still offered.
- **Python + Flask** backend, plain **HTML/CSS/JavaScript** frontend.
- **Google Maps Platform**: Maps JavaScript, Places and Routes, for the map, "near my office" answers and walking times.

## How it works

| File | What it does |
|---|---|
| `backend/matcher.py` | Gemma turns the person's message into filters (types, budget, accessibility, urgency). Code picks matching entries from `data/resources.json`, then Gemma writes a plain-language answer using only those entries. |
| `backend/advisor.py` | The chat: picks the most relevant checked records for a question, then streams Gemma's grounded answer (`/api/ask/stream`), with a no-AI fallback. |
| `backend/nearby.py` | "Near my office / any place" answers: finds the place (Census geocoder or Google Places) and ranks homes by distance with drive and transit times. |
| `backend/redact.py` | Removes SSNs, ITINs, card numbers and account numbers by their format before any text reaches the AI. |
| `backend/app.py` | Flask server for the web page and the `/api/ask`, `/api/ask/stream`, `/api/options`, `/api/match`, and read-only `/api/listings` endpoints. |
| `backend/sources.py` | Pulls records from public open-data APIs (HUD tax-credit, subsidized and housing-authority data, Alexandria's affordable rentals, the NoVA shelter map) into a review queue. Runs in the background on searches, at most once a day. |
| `backend/review.py` | Lets the team approve or reject queued records. Nothing from an API reaches users until it's approved. |
| `backend/freshness.py` | Gemma rereads listing pages and takes down ones no longer offered. It can only hide listings, never add or revive them. |
| `backend/walkable.py` | Walking-distance search: reviewed homes + Google Places + Google Routes walking times. See [WALKABILITY.md](WALKABILITY.md). |
| `backend/prompt_tools.py` | Keyword scripts that read requests and trim documents before Gemma sees them, so prompts stay small. |
| `frontend/index.html` | The web page. |
| `data/resources.json` | The hand-verified resource list. See [data/README.md](data/README.md). |

## Getting started

You need Python 3.9 or newer and a free Gemini API key from [Google AI Studio](https://aistudio.google.com).

```bash
git clone https://github.com/phonehseng/mlhhackathonbacteriagang
cd mlhhackathonbacteriagang
cp .env.example .env          # then put your key in .env
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
python backend/app.py
```

Open http://localhost:8000.

- `python backend/test_gemma.py` checks that your key works.
- Browse readable housing cards without an AI key at `http://localhost:8000/app#listings`. The raw JSON data endpoint is `http://localhost:8000/api/listings`.
- Check listings by hand at `http://localhost:8000/review`: **Verify** after a call or a look at the official page, **Flag** what needs a human check, **Hide** anything wrong (hidden records leave every list, map and chat answer). Decisions are saved to `data/listing_review.json` on your own computer only; commit that file and redeploy to publish them. The hosted site shows the page read-only.
- `python backend/catalog.py --check` validates the source catalog.
- `python -m unittest discover -s backend -p 'test_catalog.py' -v` runs offline catalog/matching/API checks.
- The starter catalog includes openings and waitlists across Northern Virginia. See [source verification notes](data/VERIFICATION.md) for dated evidence and [catalog maintenance](data/README.md) for weekly review rules. Verification is AI-assisted review of official web sources, not phone confirmation or a live vacancy feed. Closed and overdue records are excluded from matching.

## Responsible AI, privacy and accessibility

- **Grounding:** the assistant only recommends entries from our hand-verified list, and only entries marked `verified`. It's told never to invent places, phone numbers or prices, and to point people to 211 when nothing fits.
- **Safety:** every page shows 911 and 211 up front. Urgent situations list shelters first. Answers say they are guidance, not legal advice.
- **Prompt injection:** questions, chat history and catalog records are marked as data in the prompt, and the model is told not to follow instructions inside them.
- **Privacy:** uploaded documents are read on our own server (including OCR), and SSNs and account numbers are removed by pattern before anything is sent to Gemma. Users can review the cleaned text before submitting. We don't store requests. On the free Gemini API tier Google may use submitted text to improve its products, so a real deployment should use a paid key or Vertex AI. Names and addresses are not removed automatically, so the page asks people to check.
- **Accessibility:** labelled form fields, keyboard-navigable tabs, visible focus outlines, high-contrast text, and results announced to screen readers.
- **Limits:** OCR on poor photos can misread text, and the AI can still make mistakes, so answers point to real people (211, tenant legal aid) for decisions.

## Team workflow (see [CONTRIBUTING.md](CONTRIBUTING.md) for the full git guide)

- Pull before you start: `git pull`
- Work on a branch: `git checkout -b your-feature`
- Never commit secrets or API keys (`.env` is gitignored)

## License

[MIT](LICENSE)
