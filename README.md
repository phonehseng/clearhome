# Clear House

Group hackathon effort by Pierce, Umair, Phone, and Ryan for **GDG Build with AI x Hacktoberfest 2026** (Virginia Tech, Oct 24-25, 2026). Theme: **AI for Housing**.

**Live site:** https://clear-house-875094537886.us-east4.run.app

## Problem

Finding safe, affordable housing is hard for low-income people, especially students and families in crisis. Listings are scattered, fake and scam listings are common, leases are full of confusing legal language, and emergency help is hard to find when you need it fast.

## Solution

**Clear House** is an AI housing assistant for **Northern Virginia** and **Blacksburg (Virginia Tech)**, powered by Gemma 4, that helps people:

- **Find affordable housing.** Matches a person's budget, location and accessibility needs to manually verified affordable and low-income housing listings. In Blacksburg the focus is student rooms under $1,000 per person, with individual and joint leases labeled.
- **Find emergency help.** Points people to verified shelters and emergency housing resources, with urgent cases shown first.
- **Ask Gemma, live.** A chat that streams its answer as Gemma writes it, grounded in the verified list. "Near my office at …" questions are answered instantly with distances and drive/transit times (Google Places + Routes), no AI needed, and walking-time questions ("within a 15 minute walk of VT") are measured, not guessed. If Gemma is unavailable, the chat still lists matching verified resources.
- **See it on a map.** Reviewed homes on Google Maps (Leaflet fallback) with Northern Virginia and Blacksburg tabs, plus homes within walking distance of a grocery store, pharmacy or transit stop.
- **Find new listings on the web.** Gemma searches the web with Google Search grounding; results appear as orange pins labeled "not verified by our team yet".
- **Sort the listings by asking.** A mini Gemma chat above the listings answers in a few lines and moves the communities that fit to the top.
- **Listings stay current on their own.** A daily job has Gemini find new listings (thinking, Google Search, then a second reading of each source page with its quotes checked by code), renews listings still offered, takes down ones that are gone, then commits, pushes and redeploys. See [DEPLOY.md](DEPLOY.md), "Automatic listing upkeep".
- **Save favorites.** Save listing cards to a Favorites tab and share a link to one.

To avoid made-up information, the assistant only recommends places from our hand-verified resource list (`data/resources.json`, 436 records across both areas). Answers are informational and are not legal advice.

## Tech used

- **Gemma 4** (`gemma-4-26b-a4b-it`) through the Gemini API, for understanding requests, writing grounded answers (streamed live), searching the web for new listings (Google Search grounding), and checking whether listings are still offered.
- **Gemma 4 on our own Cloud Run L4 GPU** (Ollama, thinking off), so chat answers start in seconds. If the GPU is asleep or slow, the app falls back to the Gemini API. See [gemma/README.md](gemma/README.md).
- **Python + Flask** backend, plain **HTML/CSS/JavaScript** frontend.
- **Google Maps Platform**: Maps JavaScript, Places and Routes, for the map, "near my office" answers and walking times.
- **Google Cloud Run** hosts the site, with the API keys in **Secret Manager**. See [Deploy](#deploy).

## Pages

| Address | Page |
|---|---|
| `/` | Front page (`frontend/about.html`): the map of every verified home, how Clear House works, Built with Google Cloud, the open-source repo, and the "Get started" chat with Gemma (your first question carries over to the tools page). |
| `/app` | The tools (`frontend/index.html`): housing cards and filters, the map, the Gemma chat, walking distance, and Favorites. |
| `/resources` | How qualifying works, programs and where to apply, rentals and student rooms, and example questions answered by Gemma (`frontend/resources.html`). |
| `/google-cloud` | How the Google Cloud services fit together and what each one does (`frontend/google-cloud.html`). |
| `/review` | The team's listing check page (`frontend/review.html`), read-only on the hosted site. |

## How it works

| File | What it does |
|---|---|
| `backend/app.py` | Flask server for the pages and the `/api/ask`, `/api/ask/stream`, `/api/options`, `/api/match`, `/api/live-search`, read-only `/api/listings`, and listing photo (`/media/listings/<id>`) endpoints. |
| `backend/catalog.py` | Loads and validates `data/resources.json` and does the deterministic matching (budget, area, room type, eligibility). No network or AI calls. |
| `backend/matcher.py` | Gemma turns the person's message into filters (types, budget, accessibility, urgency). Code picks matching entries from `data/resources.json`, then Gemma writes a plain-language answer using only those entries. |
| `backend/advisor.py` | The chat: picks the most relevant verified records for a question, then streams Gemma's grounded answer (`/api/ask/stream`), with a no-AI fallback. |
| `backend/gemma_gpu.py` | Calls Gemma 4 on our private Cloud Run GPU first when `GEMMA_GPU_URL` is set, and gives way to the Gemini API if it doesn't answer in time. |
| `backend/nearby.py` | "Near my office / any place" answers: finds the place (Census geocoder or Google Places) and ranks homes by distance with drive and transit times. |
| `backend/walkable.py` | Walking-distance search: reviewed homes + Google Places + Google Routes walking times. See [WALKABILITY.md](WALKABILITY.md). |
| `backend/live_search.py` | Gemma searches the web for listings in an area. A result is kept only if its source is a page Google actually returned, and phone numbers are never taken from the web. |
| `backend/redact.py` | Removes SSNs, ITINs, card numbers and account numbers by their format before any text reaches the AI. |
| `backend/prompt_tools.py` | Keyword scripts that read requests and trim records before Gemma sees them, so prompts stay small. |
| `backend/sources.py` | Pulls records from public open-data APIs (HUD tax-credit, subsidized and housing-authority data, Alexandria's affordable rentals, the NoVA shelter map) into a review queue. Runs in the background on searches, at most once a day. |
| `backend/review.py` | Lets the team approve or reject queued records. Nothing from an API reaches users until it's approved. |
| `backend/freshness.py` | Gemma rereads listing pages and takes down ones no longer offered. It can only hide listings, never add or revive them. |
| `backend/add_listing.py` | Adds one listing by asking questions, so hand-added records have every field the site checks. `--dry-run` writes nothing. |
| `backend/geocode.py` | Adds map coordinates to records without them, using the free US Census Geocoder. |
| `backend/source_audit.py` | Makes each listing's main link point to the right page and labels honestly what that page is. |
| `backend/listing_photos.py` | Downloads the providers' own listing photos into `.cache/listing-photos`. They ship with the hosted site; a provider that blocks us leaves no photo, never a substitute. |
| `backend/photo_audit.py` | Reports missing, unavailable or too-small listing photos. |
| `frontend/listing-map.js` | The listings map shared by the front page and the tools page: Google Maps (Leaflet fallback), county outlines, Northern Virginia / Blacksburg tabs, Near me, and web finds. |
| `frontend/rental-labels.js` | Keeps the offered space (room or whole apartment) and payment basis worded the same on every card. |
| `frontend/interface.css` | Shared styles, such as keeping listing text copyable. |
| `data/resources.json` | The hand-verified resource list. See [data/README.md](data/README.md). |
| `gemma/` | The Gemma 4 GPU service for Cloud Run. See [gemma/README.md](gemma/README.md). |
| `video/` | A code-drawn explainer video of how Clear House works. See [video/README.md](video/README.md). |

## Getting started

You need Python 3.9 or newer and a free Gemini API key from [Google AI Studio](https://aistudio.google.com).

```bash
git clone https://github.com/phonehseng/clearhouse
cd clearhouse
cp .env.example .env          # then put your key in .env
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
python backend/app.py
```

Open http://localhost:8000.

- The map, "near my office" and walking-distance answers also need `GOOGLE_MAPS_SERVER_API_KEY` and `GOOGLE_MAPS_BROWSER_API_KEY` in `.env` (see [WALKABILITY.md](WALKABILITY.md)). Without them the map falls back to Leaflet.
- `python backend/test_gemma.py` checks that your key works.
- Browse readable housing cards without an AI key at `http://localhost:8000/app#listings`. The raw JSON data endpoint is `http://localhost:8000/api/listings`.
- Check listings by hand at `http://localhost:8000/review`: **Verify** after a call or a look at the official page, **Flag** what needs a human check, **Hide** anything wrong (hidden records leave every list, map and chat answer). Decisions are saved to `data/listing_review.json` on your own computer only; commit that file and redeploy to publish them. The hosted site shows the page read-only.
- `python backend/catalog.py --check` validates the source catalog.
- `python -m unittest discover -s backend -p "test_[!g]*.py"` runs every offline test (catalog, matching, chat, API, photos, walking times). No keys or network needed. It skips `test_gemma.py`, which calls the real API. On Windows, set `PYTHONUTF8=1` first (`$env:PYTHONUTF8=1` in PowerShell) so the data files are read as UTF-8.
- `python backend/listing_photos.py` downloads the providers' listing photos for local use and before a deploy.
- The catalog includes openings and waitlists across Northern Virginia, plus Blacksburg student rooms and affordable communities. See [source verification notes](data/VERIFICATION.md) for dated evidence and [catalog maintenance](data/README.md) for weekly review rules. Verification is AI-assisted review of official web sources, not phone confirmation or a live vacancy feed. Closed and overdue records are excluded from matching.

## Responsible AI, privacy and accessibility

> **Warning: free AI tier.** The assistant runs on Google's free Gemini tier. Google may use what you type to improve its products. Please don't enter your name, address, phone number or financial details. We automatically remove Social Security, card and account numbers, email addresses and phone numbers, but we can't remove names or street addresses.

- **Grounding:** the assistant only recommends entries from our hand-verified list, and only entries marked `verified`. It's told never to invent places, phone numbers or prices, and to point people to 211 when nothing fits.
- **Safety:** every page shows 911 and 211 up front. Urgent situations list shelters first. Answers say they are guidance, not legal advice.
- **Prompt injection:** questions, chat history and catalog records are marked as data in the prompt, and the model is told not to follow instructions inside them.
- **Privacy:** the site takes no file uploads. SSNs, account numbers, email addresses and phone numbers are removed by pattern from everything people type before it is sent to Gemma, and we don't store requests. On the free Gemini API tier Google may use submitted text to improve its products, so a real deployment should use a paid key or Vertex AI. Names and street addresses are not removed automatically, so the page asks people to keep personal details out.
- **Web finds:** listings Gemma finds on the web are labeled as not verified by our team, keep only sources Google actually returned, and never show a phone number taken from the web.
- **Accessibility:** labelled form fields, keyboard-navigable tabs, visible focus outlines, high-contrast text, and results announced to screen readers.
- **Limits:** the AI can still make mistakes, and listings change, so answers point to real people (211, tenant legal aid, the provider) for decisions.

## Deploy

The live site runs on **Google Cloud Run** in us-east4, with the Gemma and Maps keys in Secret Manager. To redeploy what's committed, download the listing photos and deploy from the project folder:

```bash
python backend/listing_photos.py
gcloud run deploy clear-house --source . --region us-east4
```

The service keeps its secrets, settings and limits; only the code changes. `cloudbuild.yaml` can redeploy on every push to `main`, but the Cloud Build trigger isn't set up yet, so deploys are by hand for now. See [DEPLOY.md](DEPLOY.md) for first-time setup, automatic deploys and changing a key.

## Team workflow (see [CONTRIBUTING.md](CONTRIBUTING.md) for the full git guide)

- Pull before you start: `git pull`
- Work on a branch: `git checkout -b your-feature`
- Never commit secrets or API keys (`.env` is gitignored)

## License

[MIT](LICENSE)
