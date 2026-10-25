# Clear House two-minute video demo

**Audience:** Hackathon judges and general viewers; **format:** 16:9 screen recording with captions; **length:** 2:00.

The video shows the current product flow on `main`: regional overview, a real catalog search, listing caveats, emergency contacts, and the role of AI. Keep the cuts quick; hold each important screen long enough to read.

## Shot list and narration

| Time | Screen action | Voiceover |
|---|---|---|
| **0:00–0:16** | Homepage hero. Keep the service-area label and main buttons visible. | “Finding a safe, affordable place can mean searching scattered listings, confusing eligibility rules, and emergency contacts when time is short. Clear House brings housing options and local support together for Northern Virginia and Blacksburg.” |
| **0:16–0:28** | Briefly show the homepage map walkthrough, then cut directly to `/app#listings`. | “The map walkthrough previews the areas we cover. Now let’s use the live catalog to find a student room near Virginia Tech.” |
| **0:28–0:48** | Click **Blacksburg Student Rooms · Under $1,000**. Let the cards load; scroll to the first result. | “One quick filter narrows the search to rooms under a thousand dollars. Filters also separate rooms from whole homes, affordable from regular rentals, and openings from waitlists.” |
| **0:48–1:10** | Pause on the first listing. Expand **Eligibility & Important Details** and point to rent basis, availability, lease detail, and source link. | “This listing shows rent per person, the lease arrangement, and what still needs confirmation. The current example is listed at $495 per person each month, but its status says contact the provider and its move-in date is unconfirmed. The provider is the source to confirm current price, eligibility, fees, and availability.” |
| **1:10–1:24** | Show the emergency support panel and the 911/211 controls. | “When someone needs help tonight, 911 and 211 are easy to find. Clear House shares local intake information; it cannot promise that a shelter has a bed.” |
| **1:24–1:48** | Show the Gemma chat/sort control, then the verified-source notice and provider links. | “Gemma helps people ask questions in plain language and sort options. Housing recommendations use reviewed catalog records; web-discovered leads are labeled unverified. Unknown details stay visible, and users can go back to the provider.” |
| **1:48–2:00** | End on the homepage title and **Get Started** button. | “Clear House is a guide, not a landlord, legal service, or application portal. We’re looking for local partners and user feedback to test whether it makes the next step easier.” |

## Recording checklist

- Confirm the hosted site is running the latest `main` build. The hosted URL was blocked from the development environment during review, so verify the deployed page from the computer and network used to record.
- Before recording, run the Blacksburg quick filter and verify the example rent, availability label, lease detail, and source link still match. Update the narration if the first result changes.
- Test Gemma and the emergency lookup on the recording network. If an integration is slow or unavailable, keep the quick-filter demonstration and show the visible 911/211 contacts; do not fake an AI answer or imply a bed is available.
- Use fictional details only. The app redacts some common contact and financial number patterns, but that is not a guarantee that every personal detail will be removed.
- Capture the UI at a readable desktop size, keep the pointer away from text, and add accurate captions. Avoid rapid scrolls and long loading screens.

## Claims to keep accurate

- Homepage coverage numbers are dated counts from the source file, not available units, verified recommendations, or people helped. The current file has 436 rows, including 17 marked unverified; the app filters and deduplicates records before showing options. The video can skip those number cards.
- Treat advertised prices as source-recorded amounts, not guaranteed current quotes. Confirm eligibility, rent, fees, dates, and vacancies with the provider.
- The current site does not upload or analyze leases, submit applications, or guide electronic signing. Do not promise those features.
- Do not claim measured user impact, community partnerships, WCAG certification, or operating costs unless the team has evidence for them.
