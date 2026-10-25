# Clear Home two-minute video demo

**Audience:** hackathon judges and general viewers. **Format:** 16:9 screen recording with captions. **Length:** 2:00.

The video follows the judges' demo order: **problem, solution, AI and track fit, impact**. Most of it shows Gemma 4
working, because AI integration is the biggest rubric line (15 points) and the reason the project exists. Record each
shot separately and cut the waiting: Gemma takes about 20 seconds when it thinks through specific needs.

## Shot list and narration

| Time | Screen action | Voiceover |
|---|---|---|
| **0:00–0:14** | **Problem.** Homepage hero, the service-area chip visible. | “Finding a safe, affordable place in Northern Virginia or near Virginia Tech means dozens of property sites, waitlists with their own rules, and emergency help that’s hard to find when time is short.” |
| **0:14–0:24** | **Solution.** Scroll to “What’s in the list”, then open `/app`. | “Clear Home puts 419 verified records in one place: apartments, student rooms, waitlists, shelters and legal aid, with Gemma 4 to ask in plain words.” |
| **0:24–0:52** | **Gemma asks, then answers.** Type *I need an apartment for me and my dog*. Click **Northern Virginia**, **$1,200–$1,800**, **1 bedroom**. Cut the wait; show Gemma’s answer, the cards and the map pins. | “A vague request gets one quick question at a time, with buttons. Then Gemma 4, running on our own Cloud Run GPU, thinks through the budget and the pet policy and answers only from verified records, with phone numbers and sources. If a pet policy isn’t on file, it says to confirm it. It never invents a place.” |
| **0:52–1:04** | **Real distances.** Ask *something close to walmart in blacksburg*. | “‘Close to Walmart’ finds the real store with Google Places and measures walking routes with Google Routes. If nothing is within a 15-minute walk, it says so.” |
| **1:04–1:13** | **Gemma sorts the list.** In Explore Rentals, click the sample *Cheapest rooms near Virginia Tech first*. | “Gemma also reorders the whole list from one sentence, with a short note on why.” |
| **1:13–1:30** | **Tonight, safely.** Homepage, **Need a place tonight?** Pick **I’m safe for now**, then **Blacksburg**. Show shelters and hotels side by side with nightly estimates. | “For tonight, a guided chat checks you’re safe first, with 911 one tap away, then shows shelters and nearby hotels with an estimated nightly cost. Messages about suicide or abuse get 988 or the domestic violence hotline instantly, with no AI in the way.” |
| **1:30–1:46** | **Track fit: Google Cloud.** `/google-cloud`, the architecture diagram. | “It’s built on Google Cloud: Gemma 4 on a Cloud Run L4 GPU, the site on Cloud Run with Secret Manager, Cloud Build and Artifact Registry, Google Maps Platform for places and walking times, and the Gemini API with Search grounding to find new listings every day.” |
| **1:46–2:00** | **Impact.** End on the homepage title and **Get Started**. | “It’s open source with a one-click deploy, so a nonprofit or campus office can run its own copy. Clear Home is a guide, not a landlord: people confirm with the provider. Try it at clearhome.live.” |

## Recording checklist

- Confirm the hosted site runs the latest `main` build, from the computer and network you record on. Use
  **clearhome.live** if it's serving; otherwise the run.app address.
- Make sure the Gemma GPU is awake before recording (open `/app` once and wait for an answer). The engine line under an
  answer should say "on our own Cloud Run L4 GPU". If Gemma is slow or unavailable, don't fake an answer: use the backup
  below.
- Run each shot once before recording and check that the listings, the Walmart answer and the hotels still match the
  narration. Update the words if a result changes.
- Use fictional details only. The app removes common contact and financial number patterns, but not names or addresses.
- Capture at a readable desktop size, keep the pointer away from text, add accurate captions, and avoid rapid scrolls.

**Backup if Gemma is unavailable:** replace 0:24–1:13 with the catalog. Open **Filters & Favorites**, click **Blacksburg Student Rooms · Under
$1,000**, expand **Eligibility & Important Details** on the first card (rent per person, lease, source), then show the
follow-up question buttons, which work without AI.

## Claims to keep accurate

- Homepage coverage numbers are counted live from the verified catalog the app serves (unverified, hidden and duplicate
  records left out; 419 of the file's 436 rows on October 25, 2026). They are records, not available units or people
  helped.
- Advertised prices are what the provider's source recorded, not guaranteed quotes. Confirm eligibility, rent, fees,
  dates and vacancies with the provider.
- The site does not upload or analyze leases, submit applications, or guide electronic signing.
- Speeds and costs: answers start in about a second for simple questions on the GPU (measured October 25). The GPU
  costs about $1 an hour while awake by Google's list price, not a measured bill. See
  [COST_AND_SETUP.md](COST_AND_SETUP.md).
- Don't claim measured user impact, community partnerships or WCAG certification unless the team has evidence.
