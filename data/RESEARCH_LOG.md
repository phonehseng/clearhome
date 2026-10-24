# Research rotation

An hourly research job works through these topics in order, one per run, then starts over.
Each run adds records to `resources.json` only from official government or provider pages,
runs `python backend/catalog.py --check` and `python backend/test_catalog.py`, and commits.

## Topics

1. Recheck listings whose `availability.review_due` is within 2 days
2. Fairfax County and Fairfax City affordable apartment listings
3. Arlington County affordable apartment listings
4. Alexandria City affordable apartment listings
5. Loudoun County affordable apartment listings
6. Prince William County, Manassas and Manassas Park affordable apartment listings
7. Senior (55+ / 62+) affordable housing across Northern Virginia
8. Accessible units and housing for people with disabilities
9. Veterans housing (HUD-VASH, SSVF) and youth / young adult housing
10. Food support and day services near shelters

Blacksburg track (runs alternate: after a Northern Virginia topic, do the next Blacksburg topic, then back):

B1. Student rooms and shared apartments near Virginia Tech, especially under $1,000 per person
B2. Whole apartments and income-restricted / LIHTC communities in Blacksburg and Christiansburg
B3. Housing authority, vouchers and rental assistance in Montgomery County and the New River Valley
B4. Shelters, emergency help and food support in the New River Valley
B5. Senior and accessible housing in Blacksburg and Christiansburg

## Log

| Date | Topic | Records added | Notes |
|---|---|---|---|
| 2026-10-24 | Initial research (shelters, programs, open-data APIs) | 90 + 413 queued | First batch |
| 2026-10-24 | 1. Recheck expiring listings | 0 | Nothing due; all review dates are 2026-10-31 |
| 2026-10-24 | 2. Fairfax County and Fairfax City listings | 14 (11 communities) | Mostly FCRHA senior housing (55+/62+) from county pages; provider sites returned 403. Phone conflicts noted for Coan Pond and Saintsbury Plaza; Redbud Glen "leasing" vs county "Opening Soon". No Fairfax City properties publish affordable rents. |
| 2026-10-24 | 3. Arlington County listings | 11 (11 communities) | 2 available now (AHC RentCafe pages), 9 from the county's Oct 5 available-CAFs list. Dropped 6 that repeat a teammate's new batch. Needs a human check: Arbor Heights rent ($1,299 provider vs $1,627 county list); several phone/address conflicts noted in records. |

### October 24, 2026 — budget listings and duplicate audit

- Compared existing housing identity, address, plan, and program fields. The repeated
  community names represented distinct floor plans, not extra independent properties;
  retained those records and grouped their presentation instead of discarding options.
- Added Virginia Gardens ($1,413 1BR), Gates of Ballston ($1,453 studio), and Harvey Hall
  ($1,475 studio) using the official unit pages; added Terwilliger Place and The Fields
  of Manassas with unknown prices/contact-for-availability rather than inferred rents.
- Preserved the distinction between mixed-income buildings and confirmed income-restricted
  units. Checked owner pages and actual building-photo links. Details and source URLs:
  [VERIFICATION.md](VERIFICATION.md#community-browsing-and-budget-expansion--october-24-2026).
- Did not use older regional rent ranges, search-only prices, or stock gallery images as
  evidence of a specific unit’s current price, vacancy, or appearance.
# Northern Virginia expansion — October 24, 2026

- Added 202 distinct communities / 204 records from reviewed county/city and owner
  sources. See [VERIFICATION.md](VERIFICATION.md#northern-virginia-directory-expansion--october-24-2026)
  for the jurisdiction counts, primary links, exclusions, publication-age caveats,
  and provider-advertised Broadfalls studio starting at $1,447.
- Did not approve the unreviewed HUD/other-source candidate queue in bulk. Existing
  resources remain intact. Combined repeated program and phase entries and kept
  unconfirmed unit rents, availability, and accessibility unknown.
- County averages, statutory program maxima, and the October 5 Alexandria vacancy
  sheet were not treated as current individual unit offers. Source identity/program
  verification is separate from confirming an open waitlist or vacant home.
- No phone or in-person confirmation was performed. Source dates are review dates;
  records expire for recommendations after October 31 without a new review.

## Blacksburg student rooms — October 24, 2026

- Added 34 records: 23 room options, six whole-apartment/affordable-community
  options and five assistance resources, across 15 housing communities.
- Prioritized under $1,000 per student. Preserved per-person versus whole-home
  prices, fixed-term installment schedules, future dates, and individual versus
  joint liability. Unknown contract rules remain unknown.
- Marked conflicting “Spring 2026”/November 2026 provider dates as unconfirmed;
  did not promise immediate occupancy or infer open waitlists. Housing Connections
  explicitly states its voucher waitlist is closed.
- Sources, price changes, exclusions and qualifications:
  [Blacksburg audit](VERIFICATION.md#blacksburg-student-rooms--october-24-2026).
- Added cross-region matching checks and a general/senior/all eligibility filter.
  NoVA-only programs are not recommended for Blacksburg; existing records remain
  intact. No live route or map coordinate was invented.
