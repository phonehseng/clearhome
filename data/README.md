# Clear Home resource catalog

`resources.json` is the canonical, versioned database used by the assistant and the read-only `/api/listings` endpoint. No separate SQL database or new service is needed for this initial catalog. Updates go through the project's Git review workflow.

Blacksburg is a second supported area, focused on **student rooms under $1,000
per person**. The first batch adds 23 room options, six whole-apartment or
affordable-community options, and five assistance resources (34 records across
15 housing communities). Use the **Blacksburg student rooms** shortcut or select
Blacksburg and **Rooms for rent**. Individual and joint agreements are labeled;
whole-apartment prices are never divided and presented as independently rentable
bedrooms. See the [source audit](VERIFICATION.md#blacksburg-student-rooms--october-24-2026).

The **Eligibility** filter defaults to excluding recorded senior-only housing.
Choose **Senior housing** or **All eligibility groups** to include it. This does
not establish individual eligibility; senior/disability programs may also serve
younger disabled applicants, and unknown rules require provider confirmation.

The initial batch was researched on **October 24, 2026**: **21 records**, consisting of **20 housing opportunities across 13 communities** (some communities have multiple floor plans) and **one city housing-program waitlist**. One housing entry is closed and retained for audit; it is not recommended. Coverage includes Arlington, Fairfax, Loudoun, and Prince William counties, plus Alexandria, Fairfax, Falls Church, Manassas, and Manassas Park cities. This is a starter catalog, not an exhaustive inventory of Northern Virginia.

Both advertised openings and open waitlists are included. See [VERIFICATION.md](VERIFICATION.md) for sources and caveats.

The October 24 Northern Virginia expansion adds **202 distinct communities / 204
records**: 201 affordable-program communities and three residential floor plans at
one regular-rental community. Most additions are documented program contacts,
not advertised vacant apartments. Directory average rents and program rent caps
are not used as offered prices. Broadfalls advertises a studio starting at $1,447;
fees and the exact unit must be confirmed with leasing. Unknown rents remain
excluded when a numeric budget is applied. See the expansion source audit in
[VERIFICATION.md](VERIFICATION.md).

## What verification means

The initial records were reviewed by the assistant against official property-manager/owner websites and, where available, public-agency publications. This is **AI-assisted source review**, not a human staff sign-off, property inspection, phone confirmation, or live inventory feed. A property may be legitimate without having a vacant unit. Indexed pages can lag provider updates.

- `verified: true` means the recorded property/program identity and stated facts have supporting official sources. It does not establish safety, tenant eligibility, or a reserved apartment.
- `last_verified` is the date sources were reviewed. It is not the publication date or a landlord confirmation date.
- `availability.checked_on`, `source_updated_on`, and `review_due` separate the review date, any known source publication date, and our next review deadline.
- Rent is a dated advertised figure, often a starting rate. Mandatory fees, utilities, deposits, income tiers, and promotions require confirmation. Unknown fields stay `null`.
- An accessibility icon or an accessible website is not proof that a vacant apartment is wheelchair accessible. `accessible` stays `null` unless accessibility of the relevant offered unit is explicitly established.
- Public leasing-office contact details only. Never add individuals' private contact details or applicant data.

## Availability states

| Status | Meaning |
| --- | --- |
| `available_now` | Provider explicitly advertises current availability; direct confirmation is still needed. |
| `advertised_vacancy` | Provider lists a vacant unit/floor plan, but the move-in date is not confirmed. |
| `upcoming` | Provider publishes a future availability date. |
| `leasing` | General lease-up/application activity, with no specific vacant-unit guarantee. |
| `waitlist_open` | Pre-applications or waitlist applications accepted; no immediate placement claim. |
| `contact_for_availability` | Affordable program/property exists, but no affordable vacancy is confirmed. |
| `closed` | Applications closed; audit-only and excluded from recommendations. |
| `needs_recheck` | Runtime-derived state when a review is overdue or future-dated. Not stored as a fresh verification. |

All dated availability claims in this starter batch expire for recommendations after **October 31, 2026**, unless genuinely rechecked. The matcher and API exclude overdue records. Never update dates merely to keep a listing visible. This deadline is an application policy, not a provider guarantee. A passing automated check does not reverify inventory.

## Fields

Existing compatibility fields remain: `id`, `name`, `type`, `address`, `phone`, `website`, `hours`, `who_it_serves`, `cost`, `accessible`, `requirements`, `source_url`, `last_verified`, and `verified`.

Additional fields:

- `community`, `record_kind`, `floor_plan`: distinguish a community from a floor-plan opportunity. These are not individual reserved apartments or a count of all units.
- `city`, `jurisdiction`, `area`, `region`, `state`: preserve county versus independent-city distinctions.
- `monthly_rent`, `rent_basis`, `currency`: numeric advertised rent for potential budget matching; unknown/conflicting/promotion-only rent stays `null`.
- `bedrooms` (`0` for studio), `bathrooms`, `square_feet`: known floor-plan attributes; `null` if unknown or variable.
- `minimum_age`, `accessibility_notes`, `notes`: eligibility and uncertainty that must remain visible in answers.
- `sources`: supporting provider/authority URLs and their roles.
- `verification_method`: how the facts were reviewed.
- `source_kind`: distinguishes a public-authority directory from a provider page.
  For directory records, `website` remains null unless an official provider link
  was established. The lease guide never treats an agency directory as a landlord
  website or scans that directory for a community-specific lease.
- `catalog_batch`: provenance tag for a reviewed expansion; it does not confer
  verification or override any matching, eligibility, or freshness check.
- `availability`: status, evidence paraphrase, source URL, checked date, next review date, optional move-in date, optional source update date.

Resource types remain `emergency_shelter`, `rental_assistance`, `legal_aid`, `affordable_listing`, `food_support`, `housing_authority`, and `other`. This batch focuses on listings and a waitlist program; it does not yet populate emergency shelters or legal aid.

## Deterministic matching

The catalog browser and `/api/listings` exclude closed, unverified, malformed, or overdue records. Numeric budget filtering excludes unknown rents and rents above budget; a matching starting rent is only a potential option, not a full-cost guarantee. Accessibility filtering requires explicit `true`. Stated age and bedroom requirements are applied where known.

Location filtering in the catalog API is text-based, not geocoding. Use `Fairfax City` or `Fairfax County` for a precise distinction. The team's existing AI matcher is maintained separately; these catalog API checks do not describe its behavior.

## Browse and validate

Start the existing Flask server. For a readable list with filters, open **http://localhost:8000/app#listings**. The following API URLs return raw JSON for developers:

- `http://localhost:8000/api/listings`
- `http://localhost:8000/api/listings?location=Arlington&max_rent=1500&bedrooms=1`
- `http://localhost:8000/api/listings?status=waitlist_open`

Optional filters: `location`, `max_rent`, `bedrooms`, `age`, `accessible=true`, and an active `status`. The endpoint includes housing opportunities and housing-program resources. Program resources do not have a unit rent; budget/bedroom filters apply to apartment opportunities. No AI key is needed to browse.

Also supported: `rental_space=all|room|entire_home` and
`age_group=all|general|senior`. API defaults remain `all`; the browser chooses
`general`. Example:
`/api/listings?location=Blacksburg&rental_space=room&max_rent=1000&age_group=general&group_by=community`.

Room records use `bedrooms: 1` for the offered bedroom, with
`shared_home_bedrooms`/`shared_home_bathrooms` for the surrounding apartment.
`price_unit`, `rent_basis`, `payment_schedule`, `lease_type`,
`lease_responsibility`, `lease_start`, and `lease_end` distinguish room payments,
fixed-term installments and full-apartment rent. Numeric budget matches compare
the quoted payment, not a guaranteed total including every fee and utility.
Unknown prices remain excluded.

`service_areas` lets a Radford or Christiansburg office explicitly serve
Blacksburg without calling that office a Blacksburg apartment. Regional matching
keeps NoVA-only services out of Blacksburg matches and Blacksburg homes out of
NoVA results. The existing open-data candidate queue remains scoped to its NoVA
sources; the Blacksburg batch was reviewed separately, not bulk-approved.

The map can center on Blacksburg. This workspace could not confirm new property
coordinates through the Census Geocoder, so no map pins or walking times were
invented. These homes remain browseable without a verified walking badge.
Browsing, filters, sources and lease-guide context need no AI key. Live AI
answers, web discovery and Google walking routes depend on the existing service
configuration. No credentials or model settings were changed.

```sh
python backend/catalog.py --check
python -m unittest discover -s backend -p 'test_catalog.py' -v
```

Before adding or updating a record: read the provider's current listing, corroborate identity with an owner/authority source when available, record the actual status, keep unresolved prices or accessibility unknown, and set a review deadline no more than seven days after the check. Preserve useful closure/conflict notes. Never mark a listing verified solely because a search snippet or third-party aggregator claims it is available.

## Sources for future expansion

Keep the team's Northern Virginia scope when adding support resources: start with official city/county housing offices, homeless-services intake lines, 211 Virginia, Legal Services of Northern Virginia, and local food banks or community action agencies. Record each service's area separately from its office address. For the current property catalog, `area` preserves the shared team field and equals the property's jurisdiction.

## Listing photos

After reconciling the latest remote catalog, **296 of 336 housing records**
have image metadata across 299 community groups. This pass adds 16 image records
that were still missing on remote main. Previously removed photos remain removed;
the newer catalog's 40 missing records are tracked in `photo_review.json`.
`photo_sources.json` records source decisions and supporting pages. Source review
does not certify vacancy, condition or provider permission. No rent, eligibility,
availability or availability-review date was changed by this pass.

Sources include property/owner/public-agency websites, official project-team
galleries and address-matched listing platforms. Provider renderings are explicitly labeled. Beasley Square uses the project owner's approved
Wikimedia Commons photograph by Beyond My Ken, captured October 4, 2021, under
CC BY-SA 4.0. Its credit, source and license appear on the card and enlarged view.
The latest catalog's existing property image choices are preserved; rendering
metadata is labeled explicitly without changing its source image.

`photo_delivery_review.json` distinguishes URL checks from catalog coverage.
Of 260 unique current image URLs, the web connector returned 178 images; delivery
of 51 could not be confirmed, and 31 newly pulled image URLs have not been checked
in this pass. Unconfirmed does not establish that a URL is broken. Direct provider
and CDN downloads are blocked in this workspace, so native dimensions and full
browser delivery have not been verified here. Some official images are small;
**do not claim every listing has a high-resolution or currently deliverable image**.

On a machine with provider access, run:

```sh
python backend/photo_audit.py --download --require-complete
```

This checks every housing record, validates downloaded images, reports native
dimensions and flags images below 1200×675. It exits unsuccessfully when images
are missing or cannot be validated. Small images are reported separately; a
successful delivery check does not certify high resolution or property identity.
The audit never enlarges images, invents replacements or changes listing facts.

`photo` metadata contains an HTTPS image `url`, supporting `source_url`,
descriptive `alt`, `credit`, `reviewed_on` and caption. `kind: "rendering"`
requires explicit labeling. Licensed archive images also carry `license_url`,
`license_name` and `captured_on`. Community/model images may differ from the
actual unit and are not proof of vacancy or condition.

The app first serves `/media/listings/<id>`, downloading only the canonical image
from approved hosts, validating its bytes and caching it in ignored
`.cache/listing-photos/`. Catalog and walking-search cards retry the same source
URL directly in the browser if the server cannot fetch it. If both fail, the
card shows an unavailable message and source link. No replacement image is
invented. To prefetch images locally, run `python backend/listing_photos.py`.

Shared `frontend/interface.css` prevents accidental selection of buttons,
navigation and decorative elements. Listing details, addresses, prices, lease
text and form input remain selectable and copyable. It does not block keyboard
navigation, clipboard shortcuts or context menus.

## Adding a listing by hand

```bash
python backend/add_listing.py            # answer the questions; it shows the record and saves only after you say yes
python backend/add_listing.py --dry-run  # practice run, never writes
```

It fills in every field the site checks: location (Blacksburg and Christiansburg are Montgomery County, New River Valley), availability with a review date 7 days out, affordability evidence, and a map pin from the Census Geocoder. It also warns when the community already has a listing of that size. Facts copied from listing sites (Zillow, Apartments.com, Rent.com and the like) are saved unverified and flagged on /review, so they stay hidden until someone confirms them from the property's own page or by phone. Then run `python backend/catalog.py --check`, commit and push.

## Open-data review queue

`candidates.json` holds records pulled from public APIs by `backend/sources.py`. They are not shown to users until approved.

```bash
python backend/sources.py                          # refresh the queue (also runs on searches, once a day)
python backend/review.py list                      # what's waiting, by source
python backend/review.py show <id>                 # one record in full
python backend/review.py approve <id> [<id> ...]   # publish records you've spot-checked
python backend/review.py approve --source hud_pha  # publish a whole source
python backend/review.py reject <id>               # drop a record for good
```

Spot-check before approving: HUD tax-credit records sometimes list an owner's office instead of the property address, and the regional shelter map was last updated in 2023.

## Automatic take-downs

`backend/freshness.py` has Gemma reread each listing's provider page (at most every 12 hours, triggered by searches) and marks it `closed` if the page clearly no longer offers it, or `needs_recheck` if the page is gone. It saves the evidence and never deletes or revives a record. Many apartment sites block automated visitors; those still drop out automatically when their 7-day `review_due` passes.

## Affordable and regular rental categories

Both categories are supported. `affordable_listing`/`affordable_property` require `affordability.status: documented` with a program description, exact supporting official source, evidence, and review date. `rental_listing` requires `affordability.status: standard_rental` with provider rental evidence and a review date. Regular means the advertised rental is recorded without claiming an income-restricted/subsidized unit; it does not prove that a building has no affordable units. Never infer program status from price or old tax-credit records alone. The catalog validator and listings API reject housing records without category evidence.

`/api/listings?housing_type=all|affordable|regular` controls browsing. Budget filtering applies to both rental categories. Park Place is now explicitly a regular advertised senior rental because its current subsidy/program status is not established. The Reserve at Eisenhower adds provider-advertised regular options. The Spire's unresolved prices remain unknown. See sources on the cards; no website review guarantees live inventory or household eligibility.

## Community cards and duplicate prevention

The flat `/api/listings` response remains available. Add `group_by=community` for one
card per community with matching records in `floor_plans`; `count` then counts community
cards/programs and `option_count` counts the matching source records. Budget, category,
location, and availability filters run before grouping. `sort=rent_asc` puts known starting
rents first, lowest to highest; unknown prices come last. `sort=recommended` keeps availability
priority. The tools page defaults to lowest rent and offers an up-to-$1,500 shortcut.

The validator rejects repeated housing options even when imports use a different ID.
Runtime loading also keeps the newest reviewed snapshot of an identical option, including
closures, so old advertisements cannot revive a newer closure. Different floor plans and
AMI/program tiers remain distinct. Community grouping uses the street address and
jurisdiction; housing-authority programs retain separate cards. Missing building numbers
also require a matching community name to avoid combining unrelated buildings on one road.

The October 24 budget expansion added five communities, three with provider-advertised
options below $1,500. See the dated expansion notes in [VERIFICATION.md](VERIFICATION.md)
for exact prices, sources, unknowns, and the mixed-income classification caveat.

```sh
python -m unittest discover -s backend -p 'test_listing_groups.py' -v
```

## Hand review

`listing_review.json` holds the team's decisions from the `/review` page: `verified` (checked by a person, with a note on how), `flagged` (needs a human check; the 2026-10-24 listing sweep's open items start here) and `hidden` (kept out of every list, map and chat answer without deleting the record). Save decisions on a local copy (`python backend/app.py`, then http://localhost:8000/review), commit the file, and redeploy.
