# Claude handoff: verified help for people needing somewhere to sleep tonight

Implement a useful **Need somewhere tonight?** experience for people in Blacksburg, Virginia, and add researched, valid local listings. The user wants actionable places to go now, with clear information about access and getting there. Research and implement this work, not just a proposal.

## Research and verify before publishing

- Search current official provider, local government, and regional coordinated-entry sources for Blacksburg, Montgomery County, and the surrounding New River Valley. Include nearby options only when clearly labeled with their actual location and distance from Blacksburg.
- Investigate emergency overnight shelter, crisis accommodation, and any seasonal overnight programs accepting people from Blacksburg. Identify options for different household types where available. Do not list ordinary apartment waitlists, daytime-only services, or general housing directories as places to sleep tonight.
- Open each source and verify the actual service, location, phone, intake process, hours, eligibility, geographic service area, fees if any, and restrictions. Prefer primary sources and follow links to the actual program. Do not infer a program's eligibility from its name.
- **Never equate an active shelter/program with an available bed.** Only describe a bed as available tonight when a reliable, current source explicitly confirms that fact, with the verification time and scope. Otherwise use **Call to confirm a bed tonight**, **Referral required**, **Intake currently closed**, or another evidence-supported status. Do not invent live capacity or claim that website research establishes admission.
- For time-sensitive claims, use the current America/New_York date/time, check source freshness, distinguish intake hours from overnight service hours, and account for weekends and holidays. Do not hardcode the date of this handoff as the date of verification.
- If no publicly verifiable live availability exists, still implement useful verified contacts and explain the call/intake steps. Report that limitation plainly. Do not leave users with false green Available now badges.

## Information each listing needs

1. Program/provider name, type of overnight accommodation, actual city, and whether it serves people currently in Blacksburg.
2. Who it accepts: individuals/families, ages, gender restrictions if applicable, accessibility information when published, and relevant intake criteria. Mark unpublished facts as unknown.
3. **What to do now:** accurate phone link, published intake hours, whether to call first, walk in, obtain a referral, or complete a screening; what happens after contacting them; documents or fees only if verified. Do not promise admission or exclude people based on invented documentation requirements.
4. **Where to go:** verified public entrance/intake address and instructions, which may differ from a mailing address or sleeping site. For confidential shelters, show the safe intake contact and do not expose a protected address or generate directions to it.
5. **Getting there:** a map/directions link to the correct public intake location, plus verified transit routes, stops, operating windows, and last-service constraints when useful. Use official transit information. Label travel estimates and origin assumptions; do not imply a bus is running now without checking. Do not promise free rides, accessible transportation, or pickup unless a source confirms it. A directions link is preferable to invented routing details.
6. What to do if intake is closed or the program is full, using a verified regional referral or after-hours contact. Ensure alternatives actually serve this area and explain their role rather than presenting a referral line as a bed.
7. Direct official source links, a genuine reviewed-at timestamp, and a clear distinction between verified service information and unconfirmed capacity.

## Product and implementation requirements

- Inspect the existing listing schema, ingestion, API filters, UI, and Gemma retrieval before changing them. Use the project's established data paths and validation.
- Provide a prominent Blacksburg tonight entry point. Prioritize actionable overnight help and current intake instructions, with nearby/regional options clearly distinguished.
- Surface a short, scannable **Call first / Intake steps / Get directions** layout. Make phone and directions actions easy to use on mobile. Explain eligibility and practical constraints in plain language.
- Keep housing rentals separate from emergency overnight services. Do not rank long-term waitlists as immediate shelter. Ensure the new records also appear correctly in relevant shelter searches and Gemma responses.
- Avoid budget filters accidentally excluding free or unknown-cost emergency services. Respect household/eligibility filters without silently claiming eligibility is confirmed.
- Prevent stale capacity claims: model capacity separately from program operating status, give any confirmed capacity a suitably short expiry, and revert to call-to-confirm when expired. Verify existing availability filters do not hide useful call-to-confirm emergency options or promote them as guaranteed openings.
- If published sources disagree, resolve with the provider's current official information where possible, record uncertainty, and avoid presenting disputed facts as verified.

## Validation and completion report

- Trace every new factual listing field to an official source. Do not use fabricated sample listings or stock addresses to fill gaps.
- Check phone numbers, public intake addresses, source links, eligibility labels, local-time hours, and directions destinations. Verify closed-intake, full/unknown-capacity, and confidential-location cases.
- Exercise Blacksburg tonight searches through the API, website, and Gemma where applicable. Check mobile layout and empty/no-confirmed-bed states. Add focused regression coverage for emergency availability semantics and relevant filters.
- Report the real programs added, their official sources, how intake and transportation work, what can and cannot be confirmed about tonight, and the checks run. State clearly if a live deployment still needs to happen.

This handoff contains no researched shelter records and makes no claim that a bed is currently available. Claude must perform the current-source research before publishing listings.
