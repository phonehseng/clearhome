# HTTP API reference

The API is served by `backend/app.py` on the same origin as the pages. Examples use `http://localhost:8000`. Send JSON with `Content-Type: application/json`; responses are JSON unless noted. There is no versioned API namespace or published stability guarantee.

JSON handlers use a shared helper that treats malformed/non-object bodies as empty. Field requirements still apply. The Flask request limit is **1 MiB**; chat and match inputs have smaller limits. A validation error commonly returns `{ "error": "…" }` with 400. Some integration failures return a successful HTTP response containing warnings or fallback text, so inspect the payload as well as status.

## Pages and static assets

| Method / route | Response |
|---|---|
| `GET /` | Landing page |
| `GET /app` | Housing tools |
| `GET /resources` | Housing resources page |
| `GET /google-cloud` | Cloud-services page |
| `GET /review` | Team review page |
| `GET /interface.css` | Shared stylesheet |
| `GET /listing-map.js`, `/rental-labels.js` | Frontend helpers |
| `GET /logo.svg`, `/favicon.svg`, `/favicon.ico`, `/apple-touch-icon.png` | Branding assets |

There is no current `/lease` page, upload API or dedicated health-check endpoint.

## Browse listings: `GET /api/listings`

No AI key is required. Results reflect catalog validation, review decisions, deduplication and current freshness filtering.

| Query | Values / behavior |
|---|---|
| `group_by` | Omit for options; `community` for grouped cards |
| `sort` | `recommended` (default), `rent_asc` |
| `housing_type` | `all` (default), `affordable`, `regular` |
| `rental_space` | `all` (default), `room`, `entire_home` |
| `age_group` | `all` (default), `general`, `senior` |
| `location` | Location text; use precise county/city names when needed |
| `max_rent` | Nonnegative finite number; unknown rents excluded by the budget filter |
| `bedrooms` | Nonnegative integer; 0 means studio |
| `age` | Nonnegative integer |
| `accessible` | `true` or `false` (default); explicit accessibility evidence required when true |
| `status` | Active status from `catalog.STATUSES`, excluding `closed` |
| `fields` | `pins` returns map fields for records with coordinates; otherwise normal fields |

```bash
curl -s 'http://localhost:8000/api/listings?location=Blacksburg&max_rent=1000&rental_space=room&group_by=community'
```

Response keys are `listings`, `count`, `option_count`, and `notice`. `count` measures returned cards/options; `option_count` is measured before grouping/pin projection. A grouped card's `floor_plans` contains differences from its base card; merge base then plan to reconstruct each option. Grouping does not establish availability of every plan. Unsupported enumerated values or invalid numeric values return 400.

## Basic matching: `POST /api/options`

Deterministic form matches without AI. Supported fields: `location`, `budget`, `bedrooms`, `accessible`, `senior`, `tonight`, `voucher`, `income`, `household`, `situation`, and `rental_space` (`room` or `entire_home`). Boolean preferences must be JSON booleans. Invalid numeric form values are generally treated as absent; unsupported service areas return 400.

```bash
curl -s http://localhost:8000/api/options \
  -H 'Content-Type: application/json' \
  -d '{"location":"Blacksburg","budget":1000,"rental_space":"room","tonight":false}'
```

Returns area-specific `listings`, `programs`, `shelters` and guidance fields. Shelters are included for urgent requests; this does not book a bed. Consult `advisor.options()` for the complete response, including evolving guidance fields.

## Chat

### `POST /api/ask`

```json
{
  "question": "How do housing waitlists work in Arlington?",
  "history": [{"role": "user", "text": "I am looking in Arlington."}],
  "profile": {"location": "Arlington", "budget": 1500, "household": 2}
}
```

A nonempty question is required and must not exceed 1,500 characters. History accepts the last four valid user/assistant turns, each trimmed to 2,000 characters. Recognized profile context includes location, budget, income, household, bedrooms, timing and boolean needs such as tonight/accessibility/senior/voucher. Input is pattern-redacted before use. Success returns `{ "answer": "…" }`. AI failures may return 503 or 500; deterministic shortcuts can answer without AI.

### `POST /api/ask/stream`

Accepts the same body, returning `text/event-stream` after initial request validation. Each event is a `data:` line containing a JSON object with `kind` and `text`, followed by a blank line. `text` is not always a string; card events can contain structured data.

```bash
curl -N http://localhost:8000/api/ask/stream \
  -H 'Content-Type: application/json' \
  -d '{"question":"Explain the difference between a waitlist and an available apartment."}'
```

| Event kind | Meaning |
|---|---|
| `status` | Lookup/progress message |
| `engine` | Source/engine description |
| `thinking` | Progress/reasoning-related note from the implemented stream path |
| `chunk` | Incremental answer text |
| `answer` | Complete cached or instant answer |
| `fallback` | Resource fallback or stream-error text |
| `cards` | Structured matching-resource cards |
| `done` | Completion marker on paths that emit it |

Not every path emits every event or a `done` marker; handle clean stream termination. An error after headers have been sent can appear as a fallback event rather than an HTTP error. The response disables proxy buffering through `X-Accel-Buffering: no`, but intermediaries still need streaming-compatible configuration.

### `POST /api/gemma/warm`

Starts optional GPU warm-up and returns `ok` and a `gpu` configuration flag. The flag means a GPU URL is configured, not that the service is ready or a model request succeeded.

### `POST /api/match`

Accepts `{ "message": "…" }`, requiring nonempty text no longer than 2,000 characters. Returns `filters` and `answer`. On a writable local instance it can start open-data refresh and freshness checks in the background. This makes it different from the read-only catalog endpoint. Do not use it as a no-side-effect health probe.

## Programs and discovery

| Route | Input / result |
|---|---|
| `GET /api/programs` | `{ "programs": […] }` containing reviewed support resources; no AI call |
| `GET /api/places` | `{ "places": […] }` of recognized area aliases/jurisdictions |
| `GET /api/boundaries` | Northern Virginia jurisdiction boundaries as GeoJSON |
| `POST /api/live-search` | `{ "location": "Woodbridge" }`; requires at least three characters; unreviewed web discoveries, optionally queued locally |

Live search needs provider access and can return 400 for invalid scope or 502 on an exception. Domain/source-grounding checks do not make results manually verified. The endpoint caps result count; clients should retain the unreviewed label and source link.

## Maps and walking routes

### `GET /api/maps-config`

Returns `{ "browser_key": null }` or the intentionally browser-visible Maps key. Server Maps and Gemini keys must not appear here. Configure browser-key website and API restrictions.

### `POST /api/housing/search`

```json
{
  "prompt": "Prefer a supermarket within a 10 minute walk in Arlington",
  "filters": {
    "location": "Arlington",
    "maxMonthlyRent": 1500,
    "requiredAmenity": "supermarket",
    "maxWalkingMinutes": 10,
    "strict": false,
    "sort": "best",
    "bedrooms": 1,
    "senior": false
  }
}
```

At least a prompt or recognized override is required. `requiredAmenity`: `supermarket`, `pharmacy`, `transit`. Walking minutes: 5, 10, 15, 20. Sort: `best`, `rent`, `walk`. Valid overrides take precedence over parsed prompt fields. This endpoint bounds bedrooms to 0–6 and positive rent below 100,000.

Returns `configured`, `filters`, `results`, and `warnings` on normal paths. Results include housing data, a nearby amenity when found, route status, match reasons, and whether the walking limit is met. Missing server credentials return `configured: false`, empty results and warnings rather than fabricated times. Strict matching needs a qualifying route; preference matching can retain unconfirmed options. Unsupported scope/input can return 400.

### `POST /api/housing/route`

Accepts `{ "housing_id": "<catalog-id>", "place_id": "<place-id>" }`. Intended for a selected search result; looks up the catalog home and calls the walking-route helper. Returns encoded `polyline`, `seconds`, and `meters` when available, or 404 when the home/route is unavailable. See the implementation for place-ID checks; it is not an authenticated record of a user's earlier search.

### `GET /api/place-photo?name=places/…/photos/…`

Fetches a validated Google place-photo name server-side and returns image bytes. Missing/failed photos return 404. Display supplied attribution when using place photos.

## Catalog images: `GET /media/listings/<resource_id>`

Looks up the canonical photo metadata; does not accept arbitrary image URLs. Successful responses contain validated cached image bytes with `X-Content-Type-Options: nosniff`. Missing record/photo returns 404. Provider download failures return 503 with no-store caching. Images have maximum byte/pixel limits and an exact hostname allowlist in `listing_photos.py`.

Current catalog/walking cards can retry the same canonical source URL directly in the browser, then display a source-link fallback. Image sources, credits, renderings and archive licenses must survive any frontend/API changes.

## Team review

`GET /api/review` returns `records`, `decisions`, and `can_edit`. It includes records that are not currently shown, validation problems and review metadata. It is a team transparency view, not an authenticated admin login.

`POST /api/review` accepts:

```json
{"id":"<catalog-id>","state":"flagged","note":"Confirm the rent with the provider."}
```

States: `verified`, `flagged`, `hidden`, `clear`. Notes must be strings of at most 500 characters. Unknown IDs return 404; invalid fields return 400. Writes require loopback access and a writable instance, otherwise 403. Success writes `data/listing_review.json` and returns `ok` plus decisions. `clear` removes an override. A review label alone does not refresh the listing's evidence dates.

## Operational boundaries

There is no general API authentication or comprehensive per-user rate limiter in this Flask app. Do not expose the debug server publicly. Production should retain read-only review behavior and appropriately restricted credentials. API documentation describes code behavior; run live integration checks separately when changing external services.
