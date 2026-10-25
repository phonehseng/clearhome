# Cost and setup for a nonprofit or community group

Clear Home is meant to be handed off. A housing nonprofit, a library or a campus office can run its own copy for little or
nothing, and add AI and maps only when they want them.

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run?git_repo=https://github.com/phonehseng/clearhome)

The button builds this repository on Cloud Run in your own Google Cloud project. It asks for three keys, and all three
are optional (see `app.json`). For a step-by-step command line setup, see [DEPLOY.md](../DEPLOY.md).

## Pick a level

| Level | What you add | What works | Running cost | Privacy |
|---|---|---|---|---|
| **Listings only** | Nothing | Listings, filters, favorites, the map (OpenStreetMap), 911/211, crisis hotlines, and chat answers built from the verified list without AI | Cloud Run only: billed per request, and it scales to zero when nobody is using it | Questions never leave your server |
| **Low cost** | `GEMINI_API_KEY`, free from [Google AI Studio](https://aistudio.google.com) | Everything above, plus the Gemma 4 chat and Gemma's sort | Gemma 4 on the Gemini API is free of charge. It has no paid tier ([Google's pricing page](https://ai.google.dev/gemini-api/docs/pricing), checked 2026-10-25) | Google uses free-tier text to improve its products. Answers are slower: Gemma thinks before answering, 40 seconds to 2 minutes in our tests |
| **Private and fast** | Gemma 4 on your own Cloud Run L4 GPU ([gemma/README.md](../gemma/README.md)) | The same, in seconds | About $1 an hour while the GPU is awake (Google's list price, not a measured bill). It scales to zero when idle; kept on all day it's about $24 | Questions stay in your own Google Cloud project |
| **Maps (optional, any level)** | `GOOGLE_MAPS_SERVER_API_KEY`, `GOOGLE_MAPS_BROWSER_API_KEY` | "Near a place" answers, measured walking times, nearby hotels, the Google map | Google Maps Platform bills per request after its free monthly usage. Hotel results are cached for 6 hours | Place names and addresses people type are sent to Google Maps |

We run the live site at the **Private and fast** level, with the Gemini API as a fallback when the GPU is busy.

## Measured on the live site (2026-10-25, GPU awake)

| Question | Prompt | Answer | First words | Whole answer |
|---|---|---|---|---|
| "How do Housing Choice Vouchers work in Alexandria?" | ~1,700 tokens | ~250 tokens | 1.2 s | 4.1 s |
| "2 bedroom apartments in Arlington under $1,800 that allow a dog" (Gemma thinks first) | ~5,400 tokens | ~780 tokens | 12.5 s | 23.3 s |
| "Rooms near Virginia Tech under $700, furnished" (Gemma thinks first) | ~7,500 tokens | ~800 tokens | 10.6 s | 20.8 s |

Tokens are estimated as characters ÷ 4. On the GPU you pay for time awake, not tokens: one awake hour (about $1) covers
roughly 150 to 900 answers at these speeds, one at a time.

## What keeps the cost down

- **Answers without AI where AI isn't needed.** Follow-up questions (area, budget, bedrooms), "near Walmart" and
  "near my office" answers, crisis hotlines and catalog browsing are all answered by code, with no model call.
- **Small prompts.** Gemma sees at most 12 matching records, not the whole catalog. Gemma's sort sees at most 25
  listings and gives up after 20 seconds, keeping the plain order.
- **Thinking only when it helps.** Gemma takes extra reasoning time only for specific needs (pets, accessibility,
  furnished, household size).
- **Caching.** Identical questions are answered from a 12-hour cache. Hotel lookups are cached for 6 hours.
- **Failing fast.** If the web search hits its quota, it rests for 20 minutes instead of retrying. The website runs
  at most 2 instances.

## Turning things off

```bash
gcloud run services update gemma4 --region us-east4 --min-instances 0
```

This lets the GPU sleep when nobody is chatting. During an event we keep one GPU awake so the first answer doesn't
wait for a cold start (a few minutes). To stop GPU spending entirely, remove `GEMMA_GPU_URL` from the website service;
the chat goes back to the Gemini API.

## Keeping the listings current

- A daily GitHub Action (`.github/workflows/listing-upkeep.yml`) refreshes open-data sources, asks Gemini to find new
  listings from official sources (each quote is checked against the page by code), re-checks listings that are due,
  runs the tests and redeploys. It needs the `GEMINI_API_KEY` repository secret (and `GCP_SA_KEY` to redeploy).
- People make the final call on the review page (`/review`, run locally). See [MAINTENANCE.md](MAINTENANCE.md).
