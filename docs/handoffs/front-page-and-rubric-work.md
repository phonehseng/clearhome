# Handoff: front page polish, accessibility and rubric gaps

> **Status: stopped on purpose.** Everything listed under "Done" is pushed to `main`. The items under "Open" were not finished, and some need a decision from the team before anyone changes them.

Please continue from here without redoing the work below. Read "Open decisions" before changing any wording or any pinned section.

## Context

Clear Home is a housing assistant for Northern Virginia and Blacksburg (see [README.md](../../README.md)). The team is preparing for a judged hackathon, and the judging rubric (100 points) covers Impact, Tech, Responsible AI and Feasibility. The front-page work in this handoff was aimed at those points. The main pages are `frontend/index.html` (tools, `/app`), `frontend/about.html` (front page, `/`), `frontend/google-cloud.html`, `frontend/resources.html` and `frontend/review.html`. The shared header is `frontend/site-header.css`.

Several teammates edit the same files, especially `frontend/about.html`. Run `git pull` before every edit, and expect merge conflicts.

## Done (all on `main`)

| What | Where |
|---|---|
| Save button on each listing card, Favorites tab, saved in the browser only | `frontend/index.html` (commit `d938edf`) |
| Built with Google: 8 flip cards replaced with 3 cards, then the flip cards were restored by a teammate (`a5b63bb`) | `frontend/about.html` |
| Title Case across headings, buttons, links and labels (questions and sentences stay as written) | all pages (landed in `3f7db2d` alongside a teammate's footer commit) |
| Front-page map tour: plays once on a timer when the map comes into view, stops when someone touches the map | `frontend/about.html` (`c605b97`) |
| Ready When You Are box in the site blue instead of navy | `frontend/about.html` (`915812c`) |
| Orange bird perched on the "F" of the headline removed (background flocks kept) | `frontend/about.html` (`5edcca8`) |
| Tools-page header has no Get Started button, since that page is where Get Started leads | `frontend/index.html` (`a01c645`) |
| Get Started button is the site blue with a white ring over the hero, then changed to a white pill with navy text over the hero (matches the hero's own white button) | `frontend/site-header.css` (`278afe3`, `bca091a`) |
| Front-page map shorter: 460px to 340px on desktop, 360px to 280px on phones | `frontend/about.html` (`278afe3`) |
| No rubber-band bounce at the top of each page (it showed a light strip above the hero) | `frontend/site-header.css` (`fa494af`) |
| "Keep scrolling" bar about half as long: pinned distances cut to 500px (flip cards, now 500 after a teammate's 520 map value was resolved to 500 in `46561a5`), 550px (chat demo) | `frontend/about.html` (`46561a5`) |
| Accessibility: tools-page `aside` changed to a labelled `section`; all text under 12px raised to 12px; page text can be selected and copied on the front, About and Resources pages | `frontend/index.html`, `about.html`, `resources.html`, `google-cloud.html` (`395cd17`) |
| Contrast: hero gradient deepened so white hero text passes (measured 5.3 to 6.5:1, was 1.6 to 2.3:1) | `frontend/about.html` (`2564766`) |
| Impact: "What's in the list" section with real counts from `data/resources.json` (436 records, 33 emergency shelters, 5 legal aid services, 82 listings with a readable rent) | `frontend/about.html` (`2564766`) |
| Privacy: email addresses and phone numbers redacted before text goes to Gemma, with tests | `backend/redact.py`, `backend/test_redact.py`, `README.md` (`2564766`) |

Axe (run in the browser with the `wcag2a` and `wcag2aa` tags) reports no violations on the front page or the tools page. Contrast on solid backgrounds passes on the tools, Google Cloud and Resources pages.

## Fix soon (small, not started)

These are small, concrete fixes. Each one names the file and the cause, so they can be done in one pass. Each is independent, so do them in separate commits.

1. **Billing test fails because its fake is out of date.** `backend/test_chat_stream.py`, test `test_catalog_answer_when_gemma_billing_fails`, defines `broken(prompt, thoughts=False)`. The real `stream_gemma` in `backend/matcher.py` (line 67) takes `think=False` too, and `advisor.py` (line 565) passes `think=`. The call therefore raises `TypeError: broken() got an unexpected keyword argument 'think'`. That exception is caught by the generic handler in `advisor.py` (line 579), so the user sees "The AI service didn't answer" instead of the billing message. **Fix:** change the fake to `def broken(prompt, thoughts=False, think=False):`. Re-run the test. It should pass without changing any app code, since `matcher.gemma_unavailable` already maps "402" and "prepayment" to the billing message.
2. **`test_gemma` fails to import.** `backend/test_gemma.py` is a manual live check, not an offline unit test. It loads `.env` and calls the Gemini API at import time, and it stops with "Set GEMINI_API_KEY in the .env file" when no key is set. The README tells people to run it by hand (`python backend/test_gemma.py`), so keep that working. **Fix options:** (a) rename it so `unittest discover` (pattern `test_*.py`) skips it, for example `check_gemma.py`, and update the README line; or (b) keep the name and guard the live call so it is skipped when no key is set. Prefer (a).
3. **Photo-card contrast on `/app`.** Axe cannot judge the 56 text spots over photos and gradients. Check them by eye in a screenshot, or measure against the rendered background. The handoff `photo-card-text-contrast.md` in this folder has the earlier measurements.

## Smaller gaps (not started, lower priority)

These don't block the rubric on their own, but each one is a visible or honesty gap.

1. **Names and street addresses reach Gemma unredacted.** Email addresses and phone numbers are now removed (`backend/redact.py`, `EMAIL_RE` and `PHONE_RE`). Names and street addresses are not. A pattern can catch a street address well, such as a house number followed by a street suffix like "St", "Rd", "Ave", "Blvd" or "Ln". It can't reliably catch names. For names, the options are a small local named-entity model or simply keeping the on-page request to leave personal details out. `redact()` runs on every chat input in `backend/app.py` (nine call sites, including the `/api/ask/stream` path). Add tests to `backend/test_redact.py` for any new pattern.
2. **The coverage numbers are typed in.** The "What's in the list" section (`frontend/about.html`, `id="coverage"`) has 436, 33, 5 and 82, plus the date "October 24, 2026." The counts come from `data/resources.json`: total records, `type == "emergency_shelter"`, `type == "legal_aid"`, and records with `monthly_rent` set. They will go stale as the list changes. Either generate them from the data at build time or serve them from an endpoint, and update the date line whenever the counts change.
3. **Get Started on the light pages is still the blue gradient.** Over the blue hero it's a white pill with navy text (`frontend/site-header.css`, the `.ch-header.over-hero` rules). On Google Cloud, Resources, Review and `/app`, it stays the blue gradient (the base `.ch-header .header-links .cl-nav-btn` rule). The owner hasn't chosen whether the light pages should match the white pill or keep the blue. Ask before changing it.
4. **Hero gradient and text selection need a sign-off.** These are covered in "Open decisions" items 6 and 7. They are listed here so they aren't missed.

## Open decisions (ask the team first)

1. **Recommended, not yet confirmed by the team: change "verified" to "reviewed" everywhere.** Reason: the data shows AI-assisted review from official web pages, without phone confirmation. The team has not confirmed this yet.
   **Original issue:** "Verified" wording does not match the data. The site says listings are "verified." In `data/resources.json`, 419 of 436 records have `verified: true`, but most of their `verification_method` text says "AI-assisted review of official … web sources … without phone confirmation of current rents, vacancies, or an open waitlist." Choose one: change "verified" to "reviewed" across the site and the chat prompts, or add phone confirmation before keeping the word. The chat prompts and the `"verified"` wording come from commit `70a17ad`. (Earlier this session the count was given as 418; the correct figure is 419.)
2. **Decided: skipped for now (owner's choice).** Do not write stakeholder or persona claims. Original issue: **Stakeholder input (Impact, 5 points).** There are no personas, interviews or documented feedback from students or families. This cannot be written from imagination. The team has to talk to real people first, then record what they said.
3. **Decided: no tracking.** The site stays free of usage data and feedback buttons. Present impact as not yet measured, and describe a later method with a partner organization. Original issue: **Measured benefit (Impact, 10 points).** The site deliberately stores no requests, so it has no usage data. Choose a method that keeps that promise, such as an optional anonymous feedback form or partner-reported outcomes. Do not invent numbers.
4. **Decided: stay on the free Gemini tier and state the risk clearly.** The warning is in the README only (added in this change). Do not add a warning on the site unless the owner asks. Original issue: **Free Gemini tier (Feasibility and privacy).**
5. **Names and street addresses** are still not removed automatically (see `backend/redact.py`). The page only asks people to leave them out.
6. **Hero gradient** was changed for contrast, so the top of the front page is darker blue than before. Someone should confirm the look is acceptable.
7. **Text selection.** The front, About and Resources pages used to block selecting text on purpose. That block was removed in `395cd17`. Put it back if the block was a deliberate choice.
8. **Photo cards on the tools page.** Axe could not judge 56 text spots over photos and gradients (`incomplete`, not `violations`). Check those by eye, or measure them with a screenshot.

## Do not undo without asking

- **Pinned scroll sections and flip cards** on the front page were restored by a teammate on purpose (`fb9a8d5`, `b8bfa06`, `a5b63bb`). The "Keep scrolling" bar is the shared `scene-progress` element created by `pinScene()` in `frontend/about.html`.
- **Flocks of birds** in the background drawings stay. Only the orange perched bird was removed, at the owner's request.
- **Google Cloud page and the "Built with Google Cloud" header link** are teammate work.

## How to check your work

- Run the local server: `python backend/app.py` (port 8000), then open `http://localhost:8000/` and `http://localhost:8000/app`.
- Backend tests, using the project virtualenv: `.venv/bin/python -m unittest discover -s backend -p 'test_*.py'`. Currently 122 tests run, with 2 known failures that also fail on the unchanged code. Both are in "Fix soon" above, with their causes: `test_gemma` (a live script picked up by discovery) and `test_catalog_answer_when_gemma_billing_fails` (a stale fake). Do not treat them as new breaks.
- Accessibility: load axe-core 4.9.1 from `https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js` in the browser and call `axe.run`. Use `runOnly: {type: 'tag', values: ['wcag2a','wcag2aa']}`. Note that `runOnly` cannot take both rules and tags at once.
- Contrast on the hero: check the gradient stops in `frontend/about.html` (the `.cl-hero` rule) and compute the ratio at each text element's vertical position. Axe does not judge text over gradients.

## Team workflow (from the memory notes)

- After every change in this repo: `git add -A`, `git commit -m "<what changed>"`, `git pull`, `git push`. Do not add co-author lines to commits or pull requests.
- Commit only as the team identity (`git config user.email` should be the BUmair GitHub no-reply address). Never commit as the old Redboy234 identity.
- Ask when something is unclear, especially before changing shared wording or a pinned section.
