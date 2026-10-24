# Housing listing source accuracy: requested fix

Claude: Please investigate and implement this user-requested fix. This file is a handoff, not a record of completed implementation.

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
