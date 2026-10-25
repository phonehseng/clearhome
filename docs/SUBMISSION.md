# Submission kit

Everything to paste into the two submission forms. **Both are due Sunday, October 25, 2026 at 12:30 PM** (the window
opens at 11:00 AM; late submissions are not accepted). One submission does not count for the other.

| | MLH (OrganizerHQ) | GDG Housing track (codingjam.dev) |
|---|---|---|
| Where | The MLH submission form | The **Virginia Tech chapter entry**, not just the umbrella page |
| Track | **Select only one:** Best Use of Google Cloud | Best Overall AI for Housing |
| Needs | Name, description, tech used, GitHub link, 2-minute video | Codebase, demo video, short description |

## Name

**Clear Home**

## One line

Ask in plain words, get verified homes, shelters and rent help in Northern Virginia and Blacksburg, from Gemma 4 on our own Google Cloud GPU.

## Short description (codingjam.dev)

Finding a safe, affordable place means searching scattered listings, decoding eligibility rules and hunting for
emergency help when time is short. Clear Home puts them in one place for Northern Virginia and Blacksburg: 419 verified
records (apartments, student rooms, waitlists, shelters and legal aid), a map, and a Gemma 4 assistant that answers in
plain words from that list only. It asks a quick question when a request is vague, gives crisis hotlines instantly,
and shows shelters and nearby hotels for tonight.

## Full description (MLH)

**The problem.** Someone looking for housing in Northern Virginia or around Virginia Tech has to search dozens of
property sites, county pages and waitlists, each with its own rules, while emergency help is buried. Prices are often
unclear (per room or per apartment?), and listings go stale.

**What Clear Home does.**
- **Ask Gemma 4 anything:** "2 bedrooms in Arlington under $1,800 that allow a dog." Gemma answers only from our
  verified list (419 records from official sources across 12 counties and cities), names each place with its phone
  number and source, and thinks longer when a request has specific needs like pets, accessibility or a household size.
- **A quick question first:** a vague request gets one question with answer buttons (area, budget, bedrooms), each with
  an "anything is fine" option, answered by code with no AI.
- **Real walking distance:** "somewhere close to Walmart" finds the actual store with Google Places and lists only homes
  a measured walk away (Google Routes), saying honestly when none qualify.
- **Tonight:** a guided chat checks the person is safe (911 first), then shows shelters, intake lines and nearby budget
  hotels with an estimated nightly cost.
- **Safety and fairness:** messages about suicide or abuse at home get 988 or the Virginia and national domestic
  violence hotlines instantly, as tap-to-call buttons. Gemma follows Virginia's fair-housing law, and personal numbers
  are removed before any AI sees a message.
- **Gemma sorts the list:** "cheapest rooms near Virginia Tech first" reorders the listings with a short note.
- **Keeps itself current:** a daily job asks Gemini (with Google Search grounding) to find new listings from official
  sources, checks every quote against the page by code, and re-checks listings that are due.

**How it's built.** Gemma 4 26B runs on our own Cloud Run NVIDIA L4 GPU, so answers start in about a second and
questions stay in our Google Cloud project; the Gemini API is the fallback. The Flask site runs on Cloud Run, with keys
in Secret Manager and images in Artifact Registry. Google Maps Platform (Maps JavaScript, Places, Routes) powers the
map, "near" answers and hotels. 190 offline tests cover the catalog, chat, safety guardrails and APIs.

**Honest limits.** Clear Home is a guide, not a landlord, legal service or application portal. Listed doesn't mean
vacant: people confirm rent, eligibility and openings with the provider.

## Tech used

Gemma 4 (26B, via Ollama on a Cloud Run GPU, and `gemma-4-26b-a4b-it` on the Gemini API) · Gemini API with Google Search
grounding · Google Cloud Run (website and NVIDIA L4 GPU service) · Cloud Build · Artifact Registry · Secret Manager ·
Google Maps Platform: Maps JavaScript API, Places API, Routes API · Python, Flask, Gunicorn · HTML, CSS, JavaScript ·
Leaflet and OpenStreetMap (map fallback) · GitHub Actions · HUD and local open-data APIs

## Links

- **Live site:** https://clearhome.live (backup: https://clear-house-875094537886.us-east4.run.app)
- **GitHub:** https://github.com/phonehseng/clearhome (MIT license)
- **How it's built:** https://clearhome.live/google-cloud
- **Video:** add the link once it's uploaded
- **Team:** Pierce, Umair, Phone and Ryan

## Why one MLH track: Best Use of Google Cloud

The MLH form allows one track. Google Cloud is where the project is strongest and easiest for judges to see: Gemma 4
served from our own Cloud Run GPU, the website on Cloud Run, Secret Manager, Cloud Build and Artifact Registry, three
Google Maps Platform APIs and the Gemini API with Search grounding, all shown on the "Built with Google Cloud" page.
Best Use of Gemma 4 is a close second if the team prefers it.

## Before you press submit

- [ ] The repo is public and has the MIT `LICENSE` file
- [ ] The video is 2 minutes or less, uploaded, and its link pasted in both forms
- [ ] MLH: exactly one track selected
- [ ] codingjam.dev: submitted to the Virginia Tech chapter entry
- [ ] The live link opens (if clearhome.live isn't serving yet, use the run.app backup)
- [ ] Submitted early in the 11:00–12:30 window
