# Handoff: stress-test findings and fixes

## Scope and result

Tested commit `683e35f422ebb9a3260369740261c4dd05f28574` on October 25, 2026, using an isolated copy of the repository. Application code and catalog data in the working checkout were not edited. This file records findings to fix; the issues below remain outstanding.

The site passed its existing suite and the selected concurrent HTTP workload, but additional tests exposed **three issues**: a chat reset race, two endpoints with the same input-type validation failure, and silently ignored invalid budgets. Do not describe the site as bug-free.

## Checks completed

| Check | Result |
| --- | --- |
| Existing automated suite | 175 tests passed in 4.476 seconds |
| Concurrent local HTTP workload | 460 requests; zero unexpected status codes, timeouts, or tested catalog count/SSE consistency failures |
| Browser checks, after correcting an ambiguous test selector | 22 passed; 1 reproduced the chat reset race |
| Additional invalid-budget browser reproduction | Confirmed: invalid negative input submits and produces unconstrained results |
| Malformed/oversized request bodies | 52 requests across two input matrices; reproduced HTTP 500 in both endpoints described below |
| AI unavailable error path | Returned an explanatory HTTP 503 with AI configuration intentionally absent; not counted as an application defect |

The HTTP workload mixed pages, local static assets, catalog variants, programs, place names, boundaries, the local find form, instant clarification JSON/SSE replies, and deliberately invalid requests. Expected HTTP 400 and read-only HTTP 403 responses were counted as successful checks, not errors.

### Local load measurements

| Concurrent clients | Requests | Elapsed | Throughput | p50 | p95 | Maximum |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 60 | 0.55 s | 109.78 requests/s | 1.48 ms | 46.49 ms | 73.65 ms |
| 8 | 160 | 1.13 s | 141.09 requests/s | 54.80 ms | 104.32 ms | 154.74 ms |
| 24 | 240 | 1.84 s | 130.50 requests/s | 171.66 ms | 267.10 ms | 323.46 ms |

These are short local bursts against Gunicorn with one worker and eight threads, not production capacity estimates or a sustained-load/soak test. The test server used read-only mode, disabled warmup, and omitted external AI and Maps credentials. No load was sent to the public deployment or external providers.

Browser coverage included the homepage, tools, resources, Google Cloud page, and review page at 1440px and 390px; no uncaught page errors or horizontal overflow occurred in those page checks. Favorites save/reload/remove, student-room quick filtering, copying a share link, embedded follow-up choices, Gemma Skip navigation, form results, malformed favorite-storage smoke checks, empty catalog results, failed/invalid-JSON catalog responses, and chat HTTP-error recovery were exercised.

External scripts were blocked for deterministic browser testing. Provider images were deliberately unavailable to exercise fallback behavior. These checks do not verify real Maps rendering, image correctness, clipboard behavior on every browser, or live AI quality.

## 1. High priority: an old chat reply reappears after the find form resets the conversation

**Where:** `frontend/index.html`, `ask()`, the streaming event loop, and the successful `#find-form` submission handler.

**Reproduction:**

1. Open `/app` and submit a chat question.
2. Keep its `/api/ask/stream` response pending for about 1.2 seconds.
3. Before it arrives, submit the find form for Blacksburg.
4. The form succeeds, resets the chat, and displays the new “I found … homes” greeting.
5. Let the previous chat response arrive. Its old answer is appended to the newly reset conversation.

The browser reproduction used a delayed SSE answer containing `OLD_REPLY_SHOULD_NOT_REAPPEAR`; that text appeared after the new find-form greeting. This was a controlled delayed response, not a live model call.

**Cause:** `chatReset` protects the assignment to `chat`, but the older request can still render messages, append history, and mutate other UI state. The browser displayed both the fresh greeting and the stale answer.

**Requested fix:** cancel the previous request when resetting and/or check a per-turn generation before every streamed UI update and final history/state commit. An outdated request must not restore choices, add content/cards, move the map, or interfere with a newer request's busy/send state. Ensure cleanup runs on success, failure, abort, and reset.

**Acceptance:** delay a chat response, submit the form, then release the response. No content or history from the old turn reappears; the composer works immediately after reset. Repeat with an old error response and with a new chat started after reset. Preserve existing follow-up retry behavior.

## 2. Medium priority: malformed enum values crash two API handlers

**Where:** `backend/app.py`, `find_options()` and `housing_walk_search()`.

Both of these requests return HTML **HTTP 500**, instead of a validation response:

```http
POST /api/options
Content-Type: application/json

{"location":"Blacksburg","rental_space":[]}
```

```http
POST /api/housing/search
Content-Type: application/json

{"filters":{"requiredAmenity":[]}}
```

An object (`{}`) reproduces the same failure. The array `['room']` also reproduced it when sent as valid JSON with double quotes.

**Cause:** `rental_space` is tested for membership in a set and `requiredAmenity` in the supported-amenities collection before confirming that either is a string. Python raises `TypeError: unhashable type: 'list'` (or `'dict'`). Normal browser controls send strings; the malformed body bypasses that assumption.

**Requested fix:** validate types and allowed values before membership operations, returning a clear JSON HTTP 400 for explicitly invalid fields. Check similar enum boundaries for the same problem. Add regression cases for arrays, objects, unknown strings, null/missing optional values, and valid choices. Do not weaken valid optional-field behavior just to reject malformed values.

## 3. Medium priority: invalid budgets silently become unrestricted searches

**Where:** `frontend/index.html`, `#find-form` and its submit handler; `backend/app.py`, `find_options().number()`.

**Browser reproduction:** enter Blacksburg and a maximum monthly budget of `-1`, then click the actual form submit button. The input's native `checkValidity()` is false, but the form has `novalidate` and still submits. HTTP 200 returns 12 listings and the assistant reports that it found homes.

**API comparison on the tested catalog:**

| Submitted budget | HTTP status | Returned listings |
| --- | --- | --- |
| null (no maximum) | 200 | 12 |
| -1 (invalid) | 200 | 12 |
| 1 (valid, tiny maximum) | 200 | 0 |

The server converts an explicitly invalid budget to `None`, so the caller receives an unconstrained result without an explanation. This can mislead someone relying on their budget constraint.

**Requested fix:** distinguish omitted optional values from explicitly invalid values. Show an accessible inline validation message in the form and return JSON HTTP 400 at the API boundary for out-of-range/nonfinite supplied numbers. Preserve documented behavior for a blank optional budget. Inspect income, household size, and bedrooms for the same issue: the API also accepted `household: 2.9` and `bedrooms: 1.9` by truncating them to integers. Do not silently round those fields or treat booleans as numbers.

**Acceptance:** invalid numbers cannot launch a broader search; field errors identify what needs correcting, blank optional values remain supported, and valid budgets continue filtering correctly.

## Still unverified

- Live Gemma/Gemini availability, GPU cold starts, answer quality, and paid-provider latency or quotas.
- Real Google Maps/Places/Routes behavior, map-key restrictions, geolocation on devices, and live hotels/web-search results.
- Provider image loading, correct property imagery, external source page health, current rents, vacancies, and eligibility.
- Cloud Run deployment, autoscaling, production networking, sustained load, multi-user sessions over time, and real mobile Safari/Firefox behavior.

Do not turn these unrun checks into claims that those features passed or failed. Coordinate any public-deployment load test separately from these local checks.

## Evidence and execution

Full evidence is saved in this workspace at `/workspace/scratch/stress-test-2026-10-25/`: `http-load.json`, `http-inputs.json`, `extra-inputs.json`, `browser-final.json`, `budget-browser.json`, and screenshots including `chat-reset-race.png`. Those scratch artifacts are not committed and may not exist on another machine; the reproducible cases and measurements above are the portable handoff.

The existing suite was run in an isolated copy with `python -m unittest discover -s backend -p 'test_*.py' -v`. The local server matched the repository's Gunicorn worker/thread configuration, with external credentials intentionally omitted. Application tests and load checks did not alter the repository's catalog or review decisions.

## Delivery instructions

Inspect the latest `main`, reproduce these findings, implement focused fixes, and add meaningful regression coverage. Keep unrelated visual and catalog work intact. Re-run the existing suite and the affected browser/network cases; report exact results and any remaining blockers.

Use the user's workflow: `git add -A`, `git commit -m "Describe the fixes"`, `git pull --rebase origin main`, then `git push origin main`. Resolve conflicts while preserving teammates' work and recheck affected behavior. Stay on `main`. This report does not itself fix these issues.
