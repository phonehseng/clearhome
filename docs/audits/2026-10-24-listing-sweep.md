# Listing data sweep — October 24, 2026

Scope: all 421 records in `data/resources.json` (322 housing records with floor-plan/community fields, 99 services). This was an offline consistency sweep of the catalog's own data. No websites were fetched, so no new vacancy, price or phone claims were made. Records are changed only when the correct value follows from the record itself. Anything else is in the human-check table below.

## What was checked

| Check | Method | Result |
| --- | --- | --- |
| Duplicate ids | Exact id count | None |
| Same community with conflicting address, phone, city, jurisdiction or coordinates across its floor-plan records | Grouped by `community` | No conflicts. Only `website` differs per floor-plan page (Fieldstone), which is expected |
| Different names at the same street address | Street number and name compared across housing records | Fieldstone Apartments and Fieldstone Senior (one site, two programs); The Ashtons and Westover Apartments (shared leasing office; see table) |
| Phones shared across communities | Digits compared | 18 shared numbers, all management-company or leasing-office lines (for example Pointe West, Raines, Wesley Housing). No action |
| Coordinates missing, swapped or out of range | Range check (VA bounding box) | None swapped or out of range. 57 housing records have no lat/lon (see table) |
| Coordinates far from the stated city | Distance to rough city centroids (>10 km flagged) | 2 flagged, both correct on review: FACETS (Fairfax County "Alexandria" 22309) and Braddock Terrace (Aldie mailing address near South Riding) |
| Coordinates outside the stated jurisdiction | Point-in-polygon against `data/nova_boundaries.geojson` | Only `falls-church-homeless-shelter` (see table). Richmond statewide services and the LAJC office are tagged "Northern Virginia" as a service area, which is intended |
| ZIP vs city/jurisdiction | ZIP prefixes per city; Alexandria ZIPs vs city/county | Consistent (22306/22309/22310 → Fairfax County; 22304/22305/22311/22314 → Alexandria City) |
| Region/area vs city | NoVA vs New River Valley rules | Consistent. Radford-based NRCA and WRC records carry `area: Blacksburg` because they serve Blacksburg |
| Phone format | Pattern check | Unusual but intentional strings: `(703) 792-3366 (TTY: 711)` ×3, `(703) 792-8810 (TTY: 711)`, `703-352-5090 ext. 1302`, `1-800-SAY-TEEN (1-800-729-8336)`, `2-1-1`. One space-separated number was normalized (below) |
| Phone area code vs region | NoVA 703/571, NRV 540, toll-free allowed | 540 in western Loudoun (Middleburg, Purcellville: 6 records) is correct for that area. 804 for Richmond DHCD is correct. Others are in the table |
| `monthly_rent` vs dollar amounts in `cost` / availability evidence | Regex for dollar amounts ≥ $300 | No disagreements |
| `rent_basis` vs `monthly_rent` | Null rent with a priced basis | 3 fixed (below). 2 room records keep `per_person_monthly` because it carries the pricing unit |
| Bedrooms vs floor-plan name | Studio / N-bed / word forms | No disagreements. 9 range plans ("1–3 bedroom community") have `bedrooms: null`, which is correct |
| Bathrooms, room layout (N×M), square feet, lease dates | Pattern and range checks | No disagreements |
| Availability dates | `available_from` < today, `review_due` < today, `upcoming` without a date, dates quoted in evidence | `review_due` is 2026-10-31 everywhere. One `available_from` is past (table). Raines and 1203 N Main date conflicts are already noted in the records |
| Senior wording vs `minimum_age` | 55+/62+/65+/"senior" vs field | No contradictions. Some senior/disability properties intentionally have no minimum age (table) |
| Type vs wording | Shelter words in rentals; rent/lease in shelters; bed-availability claims | None. No shelter record claims an open or free bed |
| Placeholder strings | TBD, N/A, null, none, TODO, empty | No placeholders. 36 empty `lease_term_notes` strings (frontend falls back to "confirm with provider"); `waitlist_status: "unknown"` ×3 is a deliberate value |
| Stray whitespace, invisible characters, mojibake | Double/trailing spaces, NBSP/zero-width, UTF-8 mis-decoding | 44 records with double or trailing spaces in `notes` (fixed). No mojibake or invisible characters. Newlines in `how_to_apply` are intentional step lists |
| URLs | Every `*url` field, including `sources`, `availability`, `affordability` and photo credits | All HTTPS |

## Fixes made

| Record id | Field | Old → new | Why |
| --- | --- | --- | --- |
| `virginia-dhcd-landlord-tenant-resources` | `phone` | `804 371 7000` → `804-371-7000` | Same number. It was the only space-separated phone in the catalog |
| `blacksburg-legacy-on-main-2-3-bedroom-community-confirm-rent` | `rent_basis` | `advertised_starting_base` → `not_published` | `monthly_rent` is null and the cost text gives only "up to approximately" figures, not a starting rent. This matches the convention of the 12 sibling whole-home affordable records |
| `blacksburg-cedar-crest-apartments-1-3-bedroom-townhomes-confirm-rent` | `rent_basis` | `advertised_starting_base` → `not_published` | `monthly_rent` is null and the cost text says "Rent not confirmed" |
| `blacksburg-ellett-road-community-1-2-bedroom-community-confirm-eligibility` | `rent_basis` | `advertised_starting_base` → `not_published` | Same as above |
| 38 records: 31 `nova-arlington-county-*` (all except the 4 in the next row), `nova-fairfax-county-ilda-s-overlook-senior-residences`, `nova-fairfax-county-oakwood-meadow-senior-residences`, `nova-loudoun-county-loudoun-view-senior-residences`, `nova-prince-william-county-park-landing`, `-the-fitzgerald`, `-the-harbor-at-quantico-creek`, `-the-landing-at-mason-s-bridge` | `notes` | `"…require provider confirmation. "` → `"…require provider confirmation."` | Trailing space. No wording changed |
| `nova-arlington-county-the-carlin`, `-claridge-house`, `-culpepper-gardens`, `-hunter-s-park-at-cherrydale`, `nova-prince-william-county-joyfield-flats-at-woodbridge`, `-the-flats-at-neabsco` | `notes` | `"confirmation.  The…"` / `"confirmation.  Owner…"` → single space | Doubled space between appended sentences. No wording changed |

In total, 48 field edits across 47 records. The file is still written as `json.dumps(indent=2, ensure_ascii=False) + "\n"` (`git diff --stat`: 48 insertions, 48 deletions). `backend/catalog.py --check` and `backend/test_catalog.py` pass.

## Needs a human check

| Record id | Issue | What to call/check |
| --- | --- | --- |
| `nova-broadfalls-efficiency`, `nova-broadfalls-one-bedroom`, `nova-broadfalls-two-bedroom` | Phone 540-565-5835 is a 540 number for a Falls Church property. It may be a call-tracking line. The official site blocks automated checks | Call it, or check broadfallsapts.com in a browser, and confirm it reaches the Broadfalls leasing office |
| `arbelo-one-bedroom`, `arbelo-two-bedroom` | Phone conflict: 703.596.8159 vs 703-890-5348 (record uses 703-890-5348) | Call both and keep the one that reaches Arbelo leasing |
| `poland-hill-senior` | Rent conflict: owner page $1,552 / $1,855 vs county guide $1,603 / $1,916. `monthly_rent` stays null because one record covers both sizes | Call (703) 219-8790 for current 1BR/2BR rents. Consider splitting into per-bedroom records |
| `blacksburg-1203-north-main-apt-m-room-a-in-4-bedroom-apartment` | Provider headline "Spring 2026" vs availability field 11/15/26 | Call (540) 953-1341 (Pointe West) for the actual move-in date |
| `blacksburg-pheasant-run-townhomes-433-janie-lane-4-bedroom-townhome`, `blacksburg-oak-manor-108-nottingham-court-4-bedroom-townhome`, `blacksburg-piedmont-1738-donlee-drive-3-bedroom-home` | Raines listings say "Available 10/01/26", which has passed, but are still posted | Call Raines (540) 951-0000 to ask whether each home is still vacant |
| `blacksburg-nrca-rent-help` | 540-381-1561 not found on NRCA's current Emergency Assistance page, which lists (540) 633-5133. The record is already withheld (`verified: false`, site returned 403) | Call NRCA and confirm the Montgomery County emergency-assistance number |
| `blacksburg-fieldstone-*` (4 records) | Phone conflict: property site 540.701.7485 vs Park Properties 540.605.8156 | Call both and keep the leasing-office line |
| `blacksburg-the-highlands-at-huckleberry-ridge-*` (5 records) | Phone conflict: property site 540.724.8575 vs Park Properties 540.552.0826 | Call both and keep the leasing-office line |
| `terwilliger-place-community` | 757 area code for an Arlington property | Check the TrueGround Housing page and confirm the leasing number |
| `nova-fairfax-county-preserve-at-westfields` | 980 (North Carolina) area code for a Chantilly property; no website on record | Check the county directory or owner site for a local leasing number |
| `nova-alexandria-city-foxchase` | 276 (SW Virginia) area code for an Alexandria property; source guide dated August 2025 | Confirm the leasing number from the property's own site |
| `nova-alexandria-city-the-foundry` | 517 (Michigan) area code for an Alexandria property; source guide dated August 2025 | Confirm the leasing number |
| `nova-alexandria-city-gables-old-town-north` | 202 (DC) area code for an Alexandria property; source guide dated August 2025 | Confirm the leasing number (it may be a regional call center) |
| `nova-loudoun-county-the-wyatt`, `nova-prince-william-county-joyfield-flats-at-woodbridge`, `margot-junior-one-to-two-bedroom` | No phone. Joyfield's owner page shows conflicting header/footer numbers | Find the official leasing number for each |
| `margot-junior-one-to-two-bedroom` | Status `upcoming` with no `available_from`; the city notice says "tentatively December 2026 and January 2027" | Leave the date null until it is firm; recheck after the Nov 2, 2026 lottery |
| `reserve-eisenhower-allison` | `available_from` 2026-10-23 has passed (status `available_now`, so not contradictory) | Recheck by `review_due` 2026-10-31. If the unit was leased, close the record |
| `falls-church-homeless-shelter` | `jurisdiction: Falls Church City`, but the geocoded point (38.8923, -77.1911) falls in Fairfax County. The provider writes "217 Gordon Road"; the record has "217 Gordons Rd" | Confirm the exact street name and which jurisdiction the site is in. Keep the city filter working either way |
| `westover-apartments-one-bedroom`, `the-ashtons-one-bedroom` | Both use the shared leasing office 5819 Washington Blvd (same coordinates). The county directory lists the buildings at 1649 N. Longfellow St and 5701 N. 10th Rd | Ask leasing (703.636.9960) which building each available unit is in, then correct the address and coordinates |
| `lindsay-hill-senior-apartments` | "Senior" in the name, but the age rule is not stated, so `minimum_age` is null. It appears in general-age searches and not in senior searches | Ask the leasing center (Community Housing Partners) for the age requirement |
| `nova-arlington-county-the-carlin`, `-claridge-house`, `-culpepper-gardens`, `-hunter-s-park-at-cherrydale` | "62 and older and disabled persons". `minimum_age` is null on purpose, since disabled applicants of any age qualify. As a result, these properties do not appear when a user filters for senior housing | Product decision: set an `eligibility_group` (for example "senior_or_disability") rather than a minimum age |
| 57 housing records (listed below) | No lat/lon, so no map pin or distance. No other record at the same address has coordinates to copy | Geocode from the official address (Census geocoder) and spot-check against the jurisdiction boundaries |

Records missing coordinates: `linden-senior`, `witter-place-closed`, `redbud-glen-one-bedroom`, `atrium-at-metro-west-two-bedroom-one-bath`, `atrium-at-metro-west-two-bedroom-two-bath`, `crest-of-alexandria-one-bedroom`, `crest-of-alexandria-two-bedroom`, `nova-fairfax-county-preserve-at-westfields`, `nova-fairfax-county-sully-at-westfields`, `nova-fairfax-county-jefferson-at-fair-oaks`, `nova-fairfax-county-the-ian`, `nova-fairfax-county-the-point-at-dunn-loring`, `nova-fairfax-county-aventon-to-aspire-huntington-station`, `nova-fairfax-county-station-on-silver`, `nova-fairfax-county-arbor-at-halley-rise`, `nova-fairfax-county-blvd-haley`, `nova-fairfax-county-faraday-park`, `nova-fairfax-county-russell-at-reston-station`, `nova-fairfax-county-skymark`, `nova-fairfax-county-the-avant-at-reston-town-center`, `nova-fairfax-county-the-edmund`, `nova-fairfax-county-hanover-springfield`, `nova-fairfax-county-adaire`, `nova-fairfax-county-brentford-at-the-mile`, `nova-arlington-county-the-spectrum`, `nova-loudoun-county-blvd-gramercy-east-blvd-flats`, `nova-loudoun-county-waxpool-apartments`, `nova-loudoun-county-the-william`, `nova-loudoun-county-shreveport-ridge`, `nova-loudoun-county-the-woods-at-westpark`, `nova-loudoun-county-stone-springs-apartments`, `nova-loudoun-county-the-wyatt`, `nova-alexandria-city-the-fields-of-alexandria`, `nova-alexandria-city-nexus-west-alex`, `nova-alexandria-city-the-point-at-eisenhower-square`, `nova-alexandria-city-the-grayson`, `nova-alexandria-city-notch-8`, `nova-alexandria-city-bell-old-town`, `nova-prince-william-county-the-fitzgerald`, `nova-prince-william-county-joyfield-flats-at-woodbridge`, `nova-prince-william-county-the-landing-at-mason-s-bridge`, `nova-falls-church-city-the-alder-at-west-falls`, `blacksburg-union-blacksburg-d5-existing-unfurnished-bedroom`, `blacksburg-union-blacksburg-d6-existing-furnished-bedroom`, `blacksburg-union-blacksburg-d2-furnished-pool-view-bedroom`, `blacksburg-fourteen35-apt-201-room-a-in-4-bedroom-apartment`, `poland-hill-senior`, `view-at-broadlands`, `william-watters-house`, `woods-at-birchwood`, `virginia-lane-middleburg`, `blacksburg-the-highlands-at-huckleberry-ridge-*` (5), `christiansburg-linden-green-apartments-1-4-bedroom-community-waitlist-closed`.

## Code-side observations (not data)

Implemented: phone links now dial only the first real number (extensions wait for the call to connect), and family and 55+ buildings at one address stay separate cards. The items above are loaded as "flagged" on the /review page (data/listing_review.json).

- **Phone links:** `tel:` links are built by stripping every non-digit (`frontend/index.html` `tel()`, `frontend/resources.html` lines ~328 and ~379). With phone strings that are correct in the data, the dialed number comes out wrong: `(703) 792-3366 (TTY: 711)` → `tel:7037923366711`, `703-352-5090 ext. 1302` → `tel:70335250901302`, `1-800-SAY-TEEN (1-800-729-8336)` → `tel:180018007298336`. Affected records: `pwa-coordinated-entry-system-hotline`, `pwc-hilda-barg-homeless-prevention-center`, `pwc-ferlazzo-emergency-shelter`, `acts-beverly-warren-emergency-shelter`, `fairfax-hpp-rotating-sites-central-western`, `second-story-teens-in-crisis`.
- **Merged cards:** `community_key()` drops the community name whenever the street address starts with a number. As a result, Fieldstone Apartments (family) and Fieldstone Senior (55+) at 300 Fieldstone Lane group into one listing card under whichever plan sorts first.

## Follow-up: map locations

Implemented: 32 of the housing records without coordinates now have them, from OpenStreetMap Nominatim (coordinates only; no listing facts). Each point was checked to fall inside the record's own county or city outline (NoVA) or near Blacksburg. `geocode_source` says whether it matched the exact address or only the street. Still without a pin: addresses neither the Census nor OpenStreetMap knows yet (mostly new construction), the two street-only addresses, and Linden Green (Simpson Road is too long for a street-level pin).
