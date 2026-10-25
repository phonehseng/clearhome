# Clear Home demo script

## Three-minute judging demo

This script follows the current pages on `main`. It uses the Blacksburg room filter because it is quick, repeatable, and shows how Clear Home distinguishes a per-person room price from a whole-apartment price. The homepage map is a recorded walkthrough; use `/app` for the live listing tools.

### Before presenting

- Confirm the hosted site is running the latest `main` build. The hosted URL could not be reached from the development environment during this check, so its deployed version was not verified.
- Open `/` in one tab and `/app#listings` in another. On the app page, click **Blacksburg Student Rooms · Under $1,000** and check that results appear.
- Test the Gemma assistant and live integrations on the network you will present from. If an AI or map lookup is unavailable, use the catalog filters and the 211/911 panel; do not invent an answer or claim a shelter bed is open.
- Use a fictional example. Do not enter a real person's name, address, phone number, email, or other private information into the demo.
- Catalog counts on the homepage are dated source-list counts, not live vacancies or people helped. The source file currently has 436 rows; the app excludes unverified or invalid records and deduplicates listings before showing them. Explain the distinction if you point to the counts.

### 0:00–0:25 — Problem and who it serves

**On screen:** Homepage hero.

**Say:** “I’m Umair, and this is Clear Home. Finding a safe, affordable place can mean searching scattered sites, decoding eligibility rules, and trying to find emergency help when time is short. We built one place to search housing and waitlists, find local support, and get plain-language guidance. The current service areas are Northern Virginia and Blacksburg, including student rooms near Virginia Tech.”

### 0:25–0:45 — Show the scope honestly

**On screen:** Scroll to **What’s in the list**. Briefly point out the map walkthrough above it.

**Say:** “This map clip shows the kind of regional browsing the app supports; I’ll use the live catalog now. These homepage figures describe a dated source inventory. They are not a count of open apartments, available shelter beds, or people served. The app filters records before it recommends them.”

### 0:45–1:35 — Find a student room

**On screen:** Open `/app#listings`, click **Blacksburg Student Rooms · Under $1,000**, and wait for the cards. Expand **Eligibility & Important Details** on the first card.

**Say:** “For a student, I can start with rooms under $1,000. The filters distinguish rooms from whole apartments, affordable housing from regular rentals, and openings from waitlists. Here the price is shown per person, and the card records the lease arrangement and what still needs to be confirmed. The provider link is the next step for current rent, fees, eligibility, move-in dates, and availability.”

**Demo note:** The current local catalog showed **University Terrace — 1213K** at **$495 per person per month**, with availability marked **Contact for availability** and the move-in date unconfirmed. Use that example only if the same card and details are still present on demo day.

### 1:35–2:00 — Save an option

**On screen:** Save the listing, then select **Favorites**.

**Say:** “A person can save options while comparing them. Favorites stay in this browser; there’s no account, and saving does not contact the landlord or reserve a unit.”

### 2:00–2:30 — Emergency support and boundaries

**On screen:** Show **Need a Safe Place Tonight?** and its 211 and 911 links. If the regional lookup is responding, select the relevant area and show the returned intake contacts.

**Say:** “If someone is in immediate danger, the page puts 911 first. For shelter help, it directs people to 211 and local intake information. We don’t promise a bed: people need to call the provider and confirm intake.”

### 2:30–3:00 — AI, trust, and close

**On screen:** Point to the verified-source notice or the Gemma chat/sort controls; finish on the provider/source links.

**Say:** “Gemma helps people ask in plain language and sort options. Housing recommendations come from the reviewed catalog; web-discovered leads are labeled unverified. We show what is unknown and send people back to the provider to confirm details. Clear Home is an information and referral tool: it does not decide eligibility, guarantee availability, give legal advice, or handle lease signing. We’re looking for feedback from students, families, and local housing organizations so we can measure whether it saves people time and improve the directory.”

## If you have five minutes

Use the extra two minutes to show one of these, not both:

- **Resources:** Open `/resources` and show a housing-program question or a source-linked resource. Explain that local facts should be confirmed with the agency.
- **How the system is built:** Open `/google-cloud` and show the service diagram. Describe the Flask site, Gemma answer path, optional Maps services, and deployment pipeline without claiming a specific per-user cost unless you have current billing evidence.

## Claims to keep precise

- Say **catalog records** or **source-list entries**, not “available homes,” when describing coverage totals.
- Say a rent is **the amount recorded on the provider source**, not a guaranteed current quote.
- Separate regular rentals, income-restricted homes, waitlists, and emergency referrals; they do not offer the same kind of help.
- Do not claim that all private information is removed. The server redacts some common contact and financial identifier patterns, but people should still avoid entering personal details.
- The current website does not upload or analyze a lease, guide electronic signing, submit an application, or send documents to a provider. Do not promise those features during the demo.
- Do not report users helped, housing placements, time saved, community partnerships, WCAG certification, or operating costs unless the team has measured or documented them.
