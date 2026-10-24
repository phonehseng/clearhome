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

## Log

| Date | Topic | Records added | Notes |
|---|---|---|---|
| 2026-10-24 | Initial research (shelters, programs, open-data APIs) | 90 + 413 queued | First batch |
| 2026-10-24 | 1. Recheck expiring listings | 0 | Nothing due; all review dates are 2026-10-31 |
| 2026-10-24 | 2. Fairfax County and Fairfax City listings | 14 (11 communities) | Mostly FCRHA senior housing (55+/62+) from county pages; provider sites returned 403. Phone conflicts noted for Coan Pond and Saintsbury Plaza; Redbud Glen "leasing" vs county "Opening Soon". No Fairfax City properties publish affordable rents. |

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
