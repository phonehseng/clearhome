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
