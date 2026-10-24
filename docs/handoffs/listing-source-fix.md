# Housing listing source accuracy: requested fix

Please investigate and implement this user-requested fix. This file is a handoff, not a record of completed implementation.

## Reported problem

The user reports that clicking **View provider source** on the **Little River Glen** card leads to a general nursing-home page instead of useful information about the actual apartments. Users need reliable property details and a meaningful view of the property.

Reference: https://www.fairfaxcounty.gov/housing/rentalhousing/senior-housing

The official county directory was checked on October 24, 2026. It lists **Little River Glen, 4001 Barker Court, Fairfax** under independent living and lists **Little River Glen IV** separately. Recheck the source when implementing because published details may change.

## Requested implementation

1. **Correct source matching.** Inspect listing data and link-selection logic. Match sources using property name, address, and housing type. Avoid confusing independent senior apartments with nearby assisted-living facilities or similarly named developments. Determine and fix the actual root cause.
2. **Useful destinations.** Prefer a verified, property-specific official website or leasing page. If only an official directory entry exists, label the link **View official county listing**. Use a section link only if it actually works. Never invent a property URL or silently substitute an unrelated provider homepage.
3. **Property details.** Provide a clear property detail view with verified rent information, eligibility, amenities, utilities, leasing contact, application or waitlist information, and source links. Mark unknown information explicitly. Follow the existing app's design and architecture.
4. **Accurate pricing and utilities.** At review, the county advertised Little River Glen at **$890–$2,315 per month**, varying by unit size and program financing, with subsidized units available and utilities included. Show source-supported information instead of a vague instruction to confirm all utilities. Keep unverified fees clearly marked. Do not imply that advertised rent establishes current availability.
5. **Relevant imagery and location.** Verify that photos depict the actual property and may be used. If verified photos are unavailable, use a clearly labeled placeholder. Add a map or address-based map link so users can locate the property. Do not present generic photos as actual property photos.
6. **Honest verification.** Set **Source reviewed** only after checking source content and confirming it matches the property. A reachable URL alone does not establish a match. Preserve the distinction between a source review date and the date a provider updated its information.
7. **Audit other listings.** Check for the same mismatched-source problem elsewhere and correct confirmed instances. Add focused checks appropriate to the existing project for mismatched properties, generic destinations, and confusion between Little River Glen and Little River Glen IV.

## Additional county details to reverify

The reviewed directory listed Little River Glen with 120 one-bedroom apartments, age eligibility of 62+, a leasing contact of 571-544-7100, and maximum incomes of $68,880 for one person and $78,720 for two people. It also listed accessible units, laundry rooms, covered walkways, a courtyard, and senior and wellness centers on site. Accessible units at a community do not establish accessibility of every available unit. Assisted living on campus does not change the apartment listing's classification to a nursing home.

## Acceptance criteria

- Opening Little River Glen provides relevant information about the correct property.
- Its external source matches the correct community and is labeled according to its actual destination.
- Little River Glen and Little River Glen IV remain distinct listings and sources.
- Photos are verified property images or clearly labeled placeholders.
- Pricing, utilities, availability, and verification labels reflect supporting evidence.
- Relevant checks pass. Report the root cause, changes made, and validation performed.

This handoff does not verify the current implementation or the currently configured outbound URL; inspect those in the repository before making changes.

---

## Implementation report (2026-10-24)

**Root cause.** The card's main link used each record's `source_url`, and for Little River Glen that was the county's
*senior-housing directory* (`fairfaxcounty.gov/housing/rentalhousing/senior-housing`), which covers 10 senior communities and
two assisted-living facilities, including nursing and medication-management text. The property-specific FCRHA page was on
file only as a secondary source, and the card labeled every link "source" regardless of where it went. The same pattern
affected most listings: 219 of 248 used a page shared by several communities (Fairfax's privately-owned list, Alexandria's
guide, Loudoun's apartment guide, county PDFs, owner community lists).

**Changes.**
- `backend/source_audit.py`: treats any link shared by more than one community (or a known guide/list) as a directory, and
  only accepts a page as the property's own if it loads and its title/heading names the community in whole words (so a
  general page that merely mentions a property, or "Terraces at Arlington View West" for "Arlington View Terrace", is
  refused; bot-blocked pages are not verified). It sets `source_url` to the best verified property page and records
  `source_kind`. 11 listings (16 communities incl. Little River Glen, Olley Glen, Morris Glen, Saintsbury Plaza, Crest of
  Alexandria, Atrium at Metro West) now point to their own page; the rest are labeled honestly as directories.
- Cards label the link by destination ("View official property page", "View owner's property page", "View property website",
  "View official county listing"), add **Show on map**, and the details panel now shows Units, Utilities, Amenities, Leasing
  contact, How to apply, and a labeled Sources list, with "Not published by the source" for unknowns.
- Little River Glen: source is https://www.fcrha.org/properties/little-river-glen/1 (rechecked 2026-10-24: 120 one-bedroom,
  62+, $890–$2,315 varying by unit and program financing, subsidized units available, utilities included, 571-544-7100,
  $68,880 / $78,720 income limits, amenities as listed). Notes state assisted living and Little River Glen IV are separate.
  The property's own site blocks automated checks, so it isn't used as a verified link. Its photo comes from the FCRHA page.
- `backend/test_listing_sources.py`: Little River Glen → its own page; LRG and LRG IV distinct; shared links labeled as
  directories; general pages, similarly named buildings and blocked pages are refused.

**Validation.** `python backend/catalog.py --check` and all `backend/test_*.py` pass; checked in the browser that the Little
River Glen card shows "View official property page" → the FCRHA page, the map link, and the new details.

**Still open.** ~209 listings only have a directory source; adding verified property pages for them is ongoing research work.
