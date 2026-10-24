# Clear House resource catalog

`resources.json` is the canonical, versioned database used by the assistant and the read-only `/api/listings` endpoint. No separate SQL database or new service is needed for this initial catalog. Updates go through the project's Git review workflow.

The initial batch was researched on **October 24, 2026**: **21 records**, consisting of **20 housing opportunities across 13 communities** (some communities have multiple floor plans) and **one city housing-program waitlist**. One housing entry is closed and retained for audit; it is not recommended. Coverage includes Arlington, Fairfax, Loudoun, and Prince William counties, plus Alexandria, Fairfax, Falls Church, Manassas, and Manassas Park cities. This is a starter catalog, not an exhaustive inventory of Northern Virginia.

Both advertised openings and open waitlists are included. See [VERIFICATION.md](VERIFICATION.md) for sources and caveats.

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
- `city`, `jurisdiction`, `region`, `state`: preserve county versus independent-city distinctions.
- `monthly_rent`, `rent_basis`, `currency`: numeric advertised rent for potential budget matching; unknown/conflicting/promotion-only rent stays `null`.
- `bedrooms` (`0` for studio), `bathrooms`, `square_feet`: known floor-plan attributes; `null` if unknown or variable.
- `minimum_age`, `accessibility_notes`, `notes`: eligibility and uncertainty that must remain visible in answers.
- `sources`: supporting provider/authority URLs and their roles.
- `verification_method`: how the facts were reviewed.
- `availability`: status, evidence paraphrase, source URL, checked date, next review date, optional move-in date, optional source update date.

Resource types remain `emergency_shelter`, `rental_assistance`, `legal_aid`, `affordable_listing`, `food_support`, `housing_authority`, and `other`. This batch focuses on listings and a waitlist program; it does not yet populate emergency shelters or legal aid.

## Deterministic matching

The backend excludes closed, unverified, malformed, or overdue catalog records before asking Gemma to explain matches. It preserves explicit frontend location/budget inputs even when model filter extraction fails. Numeric budget filtering excludes unknown rents and rents above budget; a matching starting rent is only a potential option, not a full-cost guarantee. Accessibility filtering requires explicit `true`. Stated age and bedroom requirements are applied where known. For emergencies, waitlists and future lease-ups are not offered as immediate matches. No verified shelter match currently exists in this batch; 211/911 guidance remains available.

Location filtering is text-based, not geocoding. Use `Fairfax City` or `Fairfax County` for a precise distinction. Age, income, household eligibility, and same-day placement are never guaranteed by these filters. Gemma explanations still require an API key and can make mistakes.

## Browse and validate

Start the existing Flask server and open:

- `http://localhost:8000/api/listings`
- `http://localhost:8000/api/listings?location=Arlington&max_rent=1500&bedrooms=1`
- `http://localhost:8000/api/listings?status=waitlist_open`

Optional filters: `location`, `max_rent`, `bedrooms`, `age`, `accessible=true`, and an active `status`. The endpoint includes housing opportunities and housing-program resources. Program resources do not have a unit rent; budget/bedroom filters apply to apartment opportunities. No AI key is needed to browse.

```sh
python backend/catalog.py --check
python -m unittest discover -s backend -p 'test_catalog.py' -v
```

Before adding or updating a record: read the provider's current listing, corroborate identity with an owner/authority source when available, record the actual status, keep unresolved prices or accessibility unknown, and set a review deadline no more than seven days after the check. Preserve useful closure/conflict notes. Never mark a listing verified solely because a search snippet or third-party aggregator claims it is available.
