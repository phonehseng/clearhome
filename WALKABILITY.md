# Walking-distance search ("Near groceries & transit")

Find reviewed affordable homes with a supermarket, pharmacy or bus/train stop within a walking limit,
for example: *"under $1,500 a month with a supermarket within a 10-minute walk in Arlington"*.

## How it works

1. **A keyword script reads the request** (`backend/walkable.py: parse_request`): area, max rent, place
   type, walking minutes, "preferably" (preference instead of a strict limit), bedrooms, senior. No AI call.
2. **The catalog decides which homes are real and affordable**: only reviewed `affordable_listing`
   records, filtered by area, rent, bedrooms and age, one card per building, the 6 lowest-rent checked.
3. **Google Places (New) Nearby Search** finds up to 3 candidate places around each home. Only places whose
   *main* category is the requested type count (a dollar store that also sells food isn't a supermarket).
4. **Google Routes Route Matrix** returns the actual walking duration and distance. Straight-line distance
   only sizes the search circle and is never shown as a walking time.
5. With a strict limit, homes without a verified place inside the limit are left out. With "preferably",
   they stay, sorted after the ones that qualify.
6. The page shows cards plus a Google map with the home, the place and the walking route (fetched only
   when a card is selected). On phones, a List/Map toggle switches between them.

Nothing is invented: homes with no coordinates are listed without a walking badge, failed routes show
"Walking time unavailable", missing photos show a labeled placeholder, unknown status shows "Status not verified".

## Google Cloud setup

Project: `gen-lang-client-0995218526` ("Default Gemini Project", billed to the GDP credit).

1. Enable **Places API (New)**, **Routes API** and **Maps JavaScript API**:
   ```bash
   gcloud services enable places.googleapis.com routes.googleapis.com maps-backend.googleapis.com
   ```
2. Create two keys in Google Cloud Console → APIs & Services → Credentials:
   - **Server key** (`GOOGLE_MAPS_SERVER_API_KEY`): API restriction Places API + Routes API. Used only by
     the Python backend, never sent to the browser.
   - **Browser key** (`GOOGLE_MAPS_BROWSER_API_KEY`): API restriction Maps JavaScript API; website
     restriction `http://localhost:8000/*`, `http://127.0.0.1:8000/*` and the Cloud Run URL. The page
     receives it from `/api/maps-config`.
3. Set a **budget alert** (Billing → Budgets & alerts) and, if you want a hard cap, per-API quotas
   (APIs & Services → each API → Quotas).
4. Put both keys in `.env` (see `.env.example`). For Cloud Run, store them in Secret Manager; see `DEPLOY.md`.

Without a server key the tab shows setup guidance instead of results. Without a browser key the
results still appear, with "Walking directions" links that open Google Maps.

## Cost controls

- Field masks request only the fields the page uses.
- At most 6 homes × 1 Nearby Search + 1 Route Matrix (up to 3 destinations) per search; the route line is a
  single extra request, only when a card is selected.
- Results are cached in memory for 6 hours per home, place type and walking limit.
- Google Maps Platform includes a monthly free usage allowance per SKU; check current pricing in the console.

## Endpoints

| Endpoint | What it returns |
|---|---|
| `POST /api/housing/search` | `{prompt, filters: {location, maxMonthlyRent, requiredAmenity, maxWalkingMinutes, strict, sort}}` → results, parsed filters, warnings |
| `POST /api/housing/route` | `{housing_id, place_id}` → encoded walking polyline (only to places a search returned) |
| `GET /api/place-photo?name=places/…/photos/…` | A Google place photo, fetched server-side (photo names are validated) |
| `GET /api/maps-config` | The restricted browser key, or null |

## Test

```bash
python backend/test_walkable.py                     # 12 tests with mocked Google responses
python backend/walkable.py "under \$1500 with a supermarket within a 10 minute walk"   # live, needs the server key
```

Troubleshooting: `403 PERMISSION_DENIED` usually means the API isn't enabled or the key's API
restriction doesn't include it; `RefererNotAllowedMapError` in the browser console means the page's
address isn't in the browser key's website restrictions.

## Free alternatives (tested 2026-10-24)

| Source | Data | NoVA coverage | Notes |
|---|---|---|---|
| OpenStreetMap (Overpass API) | Supermarkets with names, often hours | 454 supermarkets | Free; credit "© OpenStreetMap contributors"; ODbL share-alike |
| USDA SNAP retailer locations (ArcGIS) | Stores accepting SNAP | 6,022 in Virginia | Free federal data |
| NCES public school locations (ArcGIS) | Public schools | 514 schools | Free federal data |

These could feed a local Northern Virginia places database refreshed by a script. Walking time still
needs a routing service (Google Routes, or a free OpenStreetMap-based router such as OpenRouteService).
