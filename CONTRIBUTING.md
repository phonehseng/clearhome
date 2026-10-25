# Git guide for the team

Git only needs about six commands for this weekend.

## The idea

- The repo on GitHub is the shared copy. Each person has their own copy on their laptop.
- **Commit** saves a snapshot locally. **Push** sends it to GitHub. **Pull** gets everyone else's changes.

## First time only

```bash
git clone https://github.com/phonehseng/clearhome
cd clearhome
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Sign in to GitHub with a [personal access token](https://github.com/settings/tokens) (tick **repo**) or an SSH key. Passwords don't work.

## The daily loop

```bash
git pull                          # 1. get the latest first
# ...edit files...
git add -A                        # 2. stage your changes
git commit -m "what you did"      # 3. save a snapshot
git pull                          # 4. grab anything new again
git push                          # 5. send it to GitHub
```

`git status` shows what has changed at any time.

## Habits that prevent most problems

- Pull before you start working, and before you push.
- Commit small and often, with a short message like "add upload page".
- Avoid editing the same file at the same time as someone else. Split work by file or folder.
- For bigger changes, use a branch: `git checkout -b my-feature`, then `git push -u origin my-feature`. Merge to `main` with a pull request on GitHub.
- Never commit secrets. API keys and passwords go in `.env`, which is gitignored.

## Common errors

- **"rejected... fetch first"**: someone pushed before you. Run `git pull`, then `git push` again.
- **Merge conflict**: git marks the clashing lines with `<<<<<<<` and `>>>>>>>`. Keep the version you want, delete the markers, then `git add -A` and `git commit`. Ask a teammate if unsure.
- **"Authentication failed"**: use a token or SSH key, not your password.
- **Nothing happens on push**: you probably forgot to `git commit` first.

## Prefer no terminal?

[GitHub Desktop](https://desktop.github.com) gives a point-and-click version of the same loop (Fetch/Pull, Commit, Push).

Clear Home --- Google Places API + Walking-Distance Housing Search
Implementation instructions for an advanced AI coding model
Mission
Implement a real, polished feature in the existing Clear Home
website so a user can search for affordable housing near a supermarket
or other essential service.

Example user request:
"Find me affordable housing in Northern Virginia under $1,500 per
month with a supermarket within a 10-minute walk."

The app must use real housing records, Google Places to discover
nearby supermarkets, and a walking-routes service to calculate walking
distance/time. It should display attractive result cards and a map
showing the housing property and nearby supermarket, with photos when
the relevant API supplies them.

This file is intended to be handed directly to an advanced AI coding
model. Inspect the existing repository first, then implement the feature
in the existing architecture. Do not merely provide a plan or
mockup---make the changes, test them, and document setup.
1. Preserve the existing Clear Home design
Keep the current site's: - Dark navy background - Blue cards and
borders - Warm gold accents - Existing Clear Home logo, navigation,
typography, and spacing

Extend the current website rather than replacing it. Reuse existing
components and styling conventions. Make the feature responsive for
desktop and mobile and accessible by keyboard.
2. Expected user flow
1. The user enters a natural-language prompt.
2. An AI model extracts structured filters, including location, maximum
   rent, housing type, required amenity, and maximum walking time.
3. The app searches a verified housing database or a real
   housing-provider source for eligible properties.
4. For each housing property with a usable address/coordinate, Google
   Places searches for nearby supermarkets or grocery stores.
5. Google Routes calculates a walking route and travel time from the
   property to each candidate supermarket.
6. Properties that do not satisfy the user's required walking-time
   limit are excluded, unless the user chose to treat proximity as a
   preference.
7. Results appear as polished cards alongside an interactive map. Each
   result explains why it matched and links to the official housing
   source.
Do not use the language model to invent housing properties, rents,
availability, supermarkets, photos, distances, or eligibility
requirements.
3. Google APIs to use
Use current Google Maps Platform documentation and APIs. Confirm current
endpoint names, supported fields, photo requirements, billing, quotas,
and terms during implementation.
A. Places API (New): Nearby Search
Use Nearby Search to find nearby grocery stores/supermarkets for each
candidate housing property.
- Search for relevant place types, such as supermarket and, where
  appropriate, grocery_store.
- Use the housing property's coordinates as the search center.
- Set a sensible search radius based on the walking limit and local
  street layout. A straight-line radius is only an initial candidate
  search, not proof of walkability.
- Request only the fields the app needs (for example place ID, display
  name, location, formatted address, business status where available,
  and photo metadata when available) to control cost.
- Use field masks as required by Places API (New).
- Deduplicate places by place ID.
- Treat a Google place result as a candidate nearby business, not as
  proof that it is currently open or has verified inventory.
- Handle no results and API errors gracefully.
Documentation: - Places API overview:
https://developers.google.com/maps/documentation/places/web-service -
Nearby Search (New):
https://developers.google.com/maps/documentation/places/web-service/nearby-search -
Place photos:
https://developers.google.com/maps/documentation/places/web-service/place-photos
B. Routes API: Walking routes
Use Google Routes API to calculate the actual walking route from each
housing property to each candidate supermarket.
- Use walking travel mode where supported.
- Provide the housing property as origin and supermarket as
  destination.
- Request route distance and duration.
- Use returned route duration to evaluate the user's maximum walking
  time.
- Display distance in miles/feet or kilometers/meters according to the
  app's locale.
- Display duration as a rounded, readable estimate (for example, "9
  min walk"), but do not fabricate it.
- If walking routing fails or walking is unsupported for a route, say
  "Walking time unavailable" and do not claim the place meets a strict
  walking-time requirement.
- Do not use straight-line distance as a substitute for walking time.
- Cache results carefully where allowed by Google Maps Platform terms
  and the product's needs. Review current storage/caching rules before
  persisting Google content.
Documentation: - Routes API overview:
https://developers.google.com/maps/documentation/routes - Compute
Routes:
https://developers.google.com/maps/documentation/routes/compute_route_directions
C. Maps JavaScript API
Use the Google Maps JavaScript API for an interactive map if the project
and budget support it.

The map should: - Show a marker for the housing property and separate
markers for nearby supermarkets. - Use distinct, accessible marker
styling (for example, a house icon and grocery-cart icon). - Draw the
walking route for the selected result when supported by the API and map
implementation. - Fit the map bounds to show both the property and
supermarket without zooming too far out. - Let users select a housing
card or supermarket and highlight the corresponding marker. - On mobile,
place the map below or behind an accessible "Map / List" toggle. -
Include a fallback when the map cannot load: retain the results and
provide a link to open directions in Google Maps.

Documentation: - Maps JavaScript API:
https://developers.google.com/maps/documentation/javascript -
Directions/rendering guidance: use current Google Maps Platform
documentation and terms.
4. Pictures and image handling
Make the results visually rich, but use legitimate images only.
Supermarket photos
- If Places API returns photo metadata for a supermarket, use the
  supported Place Photos API flow and follow current Google
  attribution and display requirements.
- Do not fabricate a supermarket photo or assume every place has one.
- If no photo is available, show a polished neutral grocery-store
  placeholder or a map thumbnail instead.
- Request photo fields only when needed to avoid unnecessary API cost.
Housing photos
Google Places does not provide verified photos of an
affordable-housing unit just because its address is known. Use: 1. A
photo supplied by the official housing provider or authorized listing
source, when available; or 2. A neutral placeholder clearly presented as
illustrative.

Never use a photo of a random house as if it depicts the actual
property. Keep the source URL and attribution when required.
Map / proximity preview
For every result, show a mini map or selected-result map with: - Home
marker - Supermarket marker - Walking route, if available - A concise
distance label such as "0.4 mi · 9-minute walk" - An accessible text
description so the relationship is understandable without the map

A screenshot-like static image can supplement the interactive map, but
it must not replace accurate route data or imply an unverified route.
5. Housing data requirements
Nearby supermarket discovery does not find affordable housing by itself.
It must be combined with a housing dataset.

Create or reuse a housing data model with fields similar to:
type HousingListing = {
  id: string;
  name: string;
  address: string;
  cityOrCounty: string;
  latitude: number | null;
  longitude: number | null;
  minMonthlyRent: number | null;
  maxMonthlyRent: number | null;
  housingType: string | null;
  programType: string | null;
  eligibilitySummary: string | null;
  availabilityStatus: string | null;
  waitlistStatus: string | null;
  officialSourceName: string;
  officialSourceUrl: string;
  lastVerifiedAt: string | null;
  imageUrl: string | null;
};
Important: - Use real official housing provider/government records, with
source URLs. - Never label a property "affordable," "income-restricted,"
or "subsidized" without evidence from a reliable source. - Never infer
that a unit is available from an old page. - Distinguish "available,"
"waitlist open," "waitlist closed," "contact provider," and "status
unknown" where the source supports these states. - If coordinates are
missing, geocode the address through an appropriate, policy-compliant
workflow or ask the data administrator to verify it. Do not guess
coordinates. - Do not make up rents, eligibility, availability, or
application links. - Clearly label sample/demo data; never present it as
real.
6. Suggested backend architecture
Adapt this to the existing stack. Do not introduce a second backend if
one already exists.

Suggested server endpoint:

POST /api/housing/search

Example request:
{
  "prompt": "Affordable housing under $1500 with a supermarket within a 10-minute walk in Northern Virginia",
  "filters": {
    "location": "Northern Virginia",
    "maxMonthlyRent": 1500,
    "requiredAmenity": "supermarket",
    "maxWalkingMinutes": 10
  }
}
Suggested processing: 1. Validate the prompt and filter schema. 2.
Interpret the natural-language prompt with the configured AI model if
needed. 3. Query the housing database using location and budget filters.
4. For each candidate property with coordinates, call Places Nearby
Search. 5. Calculate walking routes for candidate supermarkets using
Routes API. 6. Keep the closest qualifying supermarket for each housing
property, or a small number of options. 7. Apply the requested strict
filters and sort order. 8. Return only fields the UI needs, including
sources and route status.

Example response shape:
{
  "results": [
    {
      "housing": {
        "id": "real-source-id",
        "name": "Official property name",
        "address": "Verified property address",
        "monthlyRentDisplay": "Source-confirmed rent or range",
        "eligibilitySummary": "Verified eligibility summary",
        "availabilityStatus": "Status from source",
        "officialSourceUrl": "https://official-provider.example/property",
        "imageUrl": null
      },
      "nearbyAmenity": {
        "placeId": "google-place-id",
        "name": "Supermarket name from Places",
        "address": "Address returned by Places",
        "photoUrl": null,
        "walkingDistanceMeters": 650,
        "walkingDurationSeconds": 540,
        "routeStatus": "available"
      },
      "matchReasons": [
        "Within the requested rent limit",
        "Supermarket within the requested walking time"
      ]
    }
  ],
  "warnings": []
}
The example values above illustrate the schema only. They are not real
search results. The implementation must return real API/source values or
explicitly labeled demo data.

Backend requirements: - Keep Google server-side API keys in environment
variables and never expose a server key in client JavaScript. - If the
Maps JavaScript API requires a browser key, use a separate restricted
browser key with HTTP referrer restrictions and only the required APIs
enabled. - Restrict API keys by API and application where possible. Set
quotas and billing alerts. - Validate all inputs, use request timeouts,
handle errors and rate limits, and avoid uncontrolled calls for every
listing. - Use server-side filtering and pagination. - Do not allow
arbitrary URLs or user input to become server-side fetch destinations. -
Avoid sending personal or sensitive information to the AI model unless
necessary. - Follow Google's current terms, attribution rules, storage
restrictions, and photo-display requirements.
7. Result-card design
Design polished cards consistent with Clear Home's navy/blue/gold
theme. Example layout (illustrative only):

\(Property image or neutral placeholder\)

Affordable housing property name
Verified address · County/City

$X–$Y/month
Rent confirmed by source, or "Contact provider for current rent"
- Supermarket: Name from Google Places
- Walk: 0.4 mi · 9 min (actual route result)
- Eligibility: Short verified summary
- Waitlist: Current source status or "Not verified"
- Why it matches: Within budget and supermarket walk limit
Actions: - "View housing details" - "Official application / provider
website" - "View walking route" - "Show on map"

Never display the sample price, sample time, or sample distance as
factual unless returned by the real data/API flow.
8. Map and result interaction
The page should have a clear list/map experience: - Desktop: housing
cards in a left column, interactive map in a right column. - Mobile:
cards first with a "Map / List" toggle or map below the filters. -
Selecting a card focuses the map on that property's home marker and its
supermarket. - Selecting a supermarket shows its name and route
details. - If a property has several qualifying supermarkets, allow the
user to choose among them. - Include a "Open walking directions in
Google Maps" link when a valid destination and origin are available. -
Include text equivalents of map information for accessibility. - Do not
show a route line or walking-time badge when route data is missing.
9. Filters and sorting
Support: - Location / county / city - Maximum monthly rent - Housing or
program type - Supermarket within 5, 10, 15, or 20 minutes walking -
Optional bus/train proximity - Waitlist status, only when reliable data
exists - Sort by lowest rent, shortest walk, or best match

A strict "within 10 minutes walking" condition must be based on the
actual walking-route duration returned by the routing service. If the
user says "preferably," treat it as a preference rather than an absolute
exclusion.
10. Performance and cost controls
Google API calls can incur costs. Implement: - Field masks requesting
only necessary fields - A reasonable Places search radius - A cap on the
number of candidate housing listings and supermarkets processed per
search - Request deduplication for repeated property/place
combinations - Sensible caching only where allowed by current API
terms - Rate limiting and error handling - Loading, empty, and error
states - A graceful fallback when the user has not configured API
credentials

Do not call Places and Routes for every property in the entire database.
First filter the housing records by region and budget, then process a
bounded set of candidates.
11. Environment setup and documentation
Add an .env.example with placeholder names only, such as:
GOOGLE_MAPS_SERVER_API_KEY=
GOOGLE_MAPS_BROWSER_API_KEY=
AI_API_KEY=
Use the project's existing naming conventions if different. Never commit
real API keys.

Document: 1. Which Google Cloud project and APIs must be enabled. 2. How
to configure billing, key restrictions, quotas, and alerts. 3. Which
environment variables are required and where each is used. 4. How to run
the app locally. 5. How to populate the verified housing dataset. 6. How
to test a search and troubleshoot API errors.

Use current official Google Maps Platform docs to verify setup steps; do
not rely on outdated API names or deprecated endpoints.
12. Acceptance tests
The work is complete only when the following scenarios are handled:
1. A user searches for affordable housing under a rent limit with a
   supermarket within 10 minutes walking.
2. The system returns only verified housing records and real nearby
   Places results.
3. Walking time is calculated from the Routes API, not guessed from
   distance.
4. A property without coordinates is flagged and does not receive an
   invented walking-time badge.
5. No supermarket is found: the UI explains that no qualifying nearby
   supermarket was verified.
6. Route API fails: show "Walking time unavailable" rather than a
   fabricated time.
7. Housing availability is unknown: show "Status not verified."
8. A photo is unavailable: show a placeholder without implying it
   depicts the property or supermarket.
9. API credentials are missing: show setup guidance or a clearly
   labeled demo mode.
10. Mobile and desktop layouts are usable, with keyboard-accessible
    controls.
11. API keys do not leak into public source code or client-visible
    server responses.
12. The map, card, walking route, source links, and filters refer to the
    same selected property and supermarket.
Add unit/integration tests appropriate to the existing stack. Use mocked
API responses in tests, but do not confuse mocked test data with live
listings in the user-facing app.
13. Implementation deliverables
When finished: - Implement the feature in the existing repository. -
List files created or changed. - Explain how to configure the Google
APIs and AI API. - State clearly which functionality is live and which
still needs credentials or verified housing data. - Run the available
tests and lint/build checks; report their actual results. - Do not claim
success for any step that was not actually tested.
Final principle
The AI interprets the user's request; the housing database establishes
which properties are real and affordable; Google Places identifies
nearby supermarkets; Google Routes determines actual walking time; and
the UI presents the evidence clearly.