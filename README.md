# mlhhackathonbacteriagang

Group hackathon effort by Pierce, Umair, Phone, and Ryan for **GDG Build with AI x Hacktoberfest 2026** (Virginia Tech, Oct 24-25, 2026). Theme: **AI for Housing**.

## Problem

Finding safe, affordable housing is hard for low-income people, especially students and families in crisis. Listings are scattered, fake and scam listings are common, leases are full of confusing legal language, and emergency help is hard to find when you need it fast.

## Solution

**Clear House** is an AI housing assistant for **Northern Virginia**, powered by Gemma 4, that helps people:

- **Find affordable housing.** Matches a person's budget, location and accessibility needs to manually verified affordable and low-income housing listings.
- **Find emergency help.** Points people to verified shelters and emergency housing resources, with urgent cases shown first.
- **Check a lease or listing.** Explains a lease in plain language, flags risky clauses, and warns about signs of a scam or fake listing.

To avoid made-up information, the assistant only recommends places from our hand-verified resource list (`data/resources.json`). The lease and scam checks are informational and are not legal advice.

## Tech used

- **Gemma 4** (`gemma-4-26b-a4b-it`) through the Gemini API, for understanding requests, writing grounded answers, explaining leases and spotting scam signs.
- **Python + Flask** backend, plain **HTML/CSS/JavaScript** frontend.
- **pypdf** and **python-docx** to read uploaded leases, and **RapidOCR** to read photos and scanned PDFs. All three run locally, with no AI service involved.

## How it works

| File | What it does |
|---|---|
| `backend/matcher.py` | Gemma turns the person's message into filters (types, budget, accessibility, urgency). Code picks matching entries from `data/resources.json`, then Gemma writes a plain-language answer using only those entries. |
| `backend/lease_checker.py` | Explains a lease (summary, key dates and costs, clauses to watch, questions to ask) or checks a listing for scam red flags. |
| `backend/extract_text.py` | Reads PDF, Word, text and image uploads into plain text, on our own server. |
| `backend/redact.py` | Removes SSNs, ITINs, card numbers and account numbers by their format before any text reaches the AI. |
| `backend/app.py` | Flask server for the web page and the `/api/match`, `/api/lease`, `/api/listing`, `/api/extract`, and read-only `/api/listings` endpoints. |
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
- `python backend/catalog.py --check` validates the source catalog.
- `python -m unittest discover -s backend -p 'test_catalog.py' -v` runs offline catalog/matching/API checks.
- The starter catalog includes openings and waitlists across Northern Virginia. See [source verification notes](data/VERIFICATION.md) for dated evidence and [catalog maintenance](data/README.md) for weekly review rules. Verification is AI-assisted review of official web sources, not phone confirmation or a live vacancy feed. Closed and overdue records are excluded from matching.

## Responsible AI, privacy and accessibility

- **Grounding:** the assistant only recommends entries from our hand-verified list, and only entries marked `verified`. It's told never to invent places, phone numbers or prices, and to point people to 211 when nothing fits.
- **Safety:** every page shows 911 and 211 up front. Urgent situations list shelters first. Lease and listing results say they are information, not legal advice, and scam results are framed as an estimate, not a verdict.
- **Prompt injection:** pasted leases and listings are marked as data in the prompt, and the model is told not to follow instructions inside them.
- **Privacy:** uploaded documents are read on our own server (including OCR), and SSNs and account numbers are removed by pattern before anything is sent to Gemma. Users can review the cleaned text before submitting. We don't store requests. On the free Gemini API tier Google may use submitted text to improve its products, so a real deployment should use a paid key or Vertex AI. Names and addresses are not removed automatically, so the page asks people to check.
- **Accessibility:** labelled form fields, keyboard-navigable tabs, visible focus outlines, high-contrast text, and results announced to screen readers.
- **Limits:** OCR on poor photos can misread text, and the AI can still make mistakes, so answers point to real people (211, tenant legal aid) for decisions.

## Team workflow (see [CONTRIBUTING.md](CONTRIBUTING.md) for the full git guide)

- Pull before you start: `git pull`
- Work on a branch: `git checkout -b your-feature`
- Never commit secrets or API keys (`.env` is gitignored)

## License

[MIT](LICENSE)

## Guided lease review

Choose **Guide me through this lease** on a listing card. Communities with several floor
plans ask you to choose a plan first. `/lease?listing=<catalog-id>` keeps that exact plan
attached to a five-step guide: prepare, get the document, understand it, sign/submit with
the provider, and prepare for move-in.

- Users can upload/paste a lease or load a public provider reference. Public-document
  lookup starts automatically in the background and never blocks the upload option.
- `backend/lease_journey.py` checks up to two catalog-linked provider pages for same-host
  lease PDFs. It ignores application/brochure links, rejects redirects and private
  network addresses, limits download size and page count, and checks PDF text. This
  is a limited public-page lookup, not access to an applicant's account or verification
  that a document is the final lease for their unit. Every imported public document is
  labeled a reference, even if it looks like a complete lease.
- If no public PDF is found, or a provider blocks access/requires sign-in, the user can
  request the full proposed lease and addenda from leasing and upload their copy.
  Cross-host document services and JavaScript-only document links are not imported.
- Up to 120,000 characters can be reviewed in parts of at most 12,000 characters. The UI
  tracks exactly which parts have an explanation; it does not silently truncate a long
  lease or claim a partial review is complete. Oversized uploads must be separated.
  Follow-up questions use only the selected part, via `/api/lease/question`.
- Analysis uses the existing AI service and configuration. Users review extracted text
  before sending it for analysis; number-pattern redaction does not remove all personal
  data. Explanations, questions, and extraction responses use `Cache-Control: no-store`.
  Only public provider lookup results are briefly cached in server memory.
- Document text and checklists remain in the current tab, with no account history or
  browser storage. Changing the plan clears the previous document/review; changing text
  invalidates explanations and final-document confirmations. Downloadable review notes
  are not a contract, signature, or submission receipt.
- Signing, identity checks, payments, and document delivery take place through the
  provider's official process. Clear House never submits a form, adds a signature, sends
  a document, or infers acceptance from opening a link. Submission checkboxes are the
  user's own record. Confirm the final contract and save the provider's confirmation.

The new guide is `frontend/lease.html`. Metadata and public lookup use
`GET /api/listings/<id>/lease` and `GET /api/listings/<id>/lease/document`.

```bash
python -m unittest discover -s backend -p 'test_lease_journey.py' -v
```

The retrieval tests use synthetic HTML/PDF fixtures and mocked network responses. They
do not establish that a provider currently publishes a lease or that the AI has reviewed
an actual renter's lease. The provider pages reviewed while building this flow included
[Virginia Gardens](https://www.virginiagardensapts.com/) and
[Indigo at McLean Station](https://www.indigomcleanstation.com/); no public final lease was
established from those pages.
