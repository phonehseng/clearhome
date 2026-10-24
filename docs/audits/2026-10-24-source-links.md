# Source link audit — October 24, 2026

Scope: the 395-record working catalog at `70d456868f7eddae62713c14745bd1ce424f4fba`, including 299 housing listings. This is not a validation of later GitHub commits.

Checked 435 unique source, provider, application, and photo-credit page URLs: 406 loaded, 20 denied access, and 9 returned HTTP 404. A further replacement eviction-prevention page was fetched successfully. TLS verification remained enabled.

## Changes

- Replaced the LSNV tenants-and-eviction-prevention 404 with its official `/explore-legal-issues/eviction-prevention/` page (HTTP 200 and relevant page title).
- Removed 12 photo entries with failed or access-blocked credit pages; updated the photo manifest and review queue. Working property pages were not substituted for photo credits unless the exact image could be confirmed.
- Removed two access-blocked supporting references and three access-blocked optional website links.
- Withheld 14 records by setting `verified: false` and recording `source_link_audit` metadata. Their primary pages denied automated access. Raw records remain available for review; this is not evidence that the properties or services are invalid.

## Withheld records

| Record | Primary-page HTTP status |
| --- | --- |
| LAWS (Loudoun Abused Women's Shelter) 24-Hour Domestic Violence & Sexual Assault Hotline (`laws-24-hour-hotline`) | 403 |
| LAWS Emergency Shelter (domestic violence & sexual assault) (`laws-emergency-shelter`) | 403 |
| NVFS Family Shelter (SERVE Campus) (`nvfs-family-shelter-serve-campus`) | 403 |
| ACTS Turning Points 24/7 Domestic Violence Hotline and Safe House (`acts-domestic-violence-hotline`) | 403 |
| ACTS Sexual Assault Services 24/7 Hotline (`acts-sexual-assault-hotline`) | 403 |
| Northern Virginia Family Service (NVFS) - Housing Programs including Regional Housing Assistance Program (RHAP) (`nvfs-regional-housing-assistance-program`) | 403 |
| The Landing at Mason’s Bridge (`nova-prince-william-county-the-landing-at-mason-s-bridge`) | 403 |
| Alight Blacksburg — East · bedroom in 4×2 (`blacksburg-alight-blacksburg-east-bedroom-in-4-2`) | 403 |
| Alight Blacksburg — West · bedroom in 4×2 (`blacksburg-alight-blacksburg-west-bedroom-in-4-2`) | 403 |
| Alight Blacksburg — Standard · bedroom in 2×1 (`blacksburg-alight-blacksburg-standard-bedroom-in-2-1`) | 403 |
| Alight Blacksburg — Fireplace · bedroom in 2×1 (`blacksburg-alight-blacksburg-fireplace-bedroom-in-2-1`) | 403 |
| New River Community Action — housing crisis intake (`blacksburg-nrca-intake`) | 403 |
| NRCA / Montgomery County Emergency Assistance (`blacksburg-nrca-rent-help`) | 403 |
| Housing Connections — Montgomery County vouchers (`blacksburg-housing-connections`) | 403 |

## Validation and limits

- All 1953 structured source, provider, evidence, and photo-credit references attached to the 381 public catalog records have a successful response in this audit.
- The public listings and programs endpoints return HTTP 200 and exclude withheld records.
- Catalog validation and 45 existing catalog, listing, photo, source, and regional tests pass. The photo route test now uses an isolated fixture rather than assuming a particular live property always has a photo.
- The audit checks current page responses. It does not certify current vacancy, prices, eligibility, ownership, or property existence. Name/address text matches are review signals, not definitive identity verification.
- Image asset health, third-party search results, and external URLs in free-text notes are not guaranteed by the structured-source check. Websites can change or respond differently to a person’s browser.
- Keep the withheld records out of public results until a reviewer checks the primary page and current property or service details. Restore `verified: true` only after evidence is recorded; do not treat an automated access denial as a fake listing.

## Integration with latest main

Reapplied the audit edits after pulling `091bbc7`. All newer shelter metadata, photos, and 14 additional catalog records were preserved. The 435-URL audit above describes the earlier 395-record snapshot; it does not certify links introduced by those newer commits. The audited records retained the same primary URLs. Photo review metadata was reconciled against the combined catalog.
