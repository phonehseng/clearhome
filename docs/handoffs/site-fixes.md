# Handoff: fix the issues found in the full site check

A full local test of Clear House on 2026-10-24 found the problems below. Fix each one, verify it, and push. Most of the site works and should not be touched: the find form, the map, listings browsing and filters, Show more/Show all, the photo dialog, the chat fallbacks and every page link passed. Pull first (`git pull`), because teammates push often and may already have changed these files.

## Ground rules (from the project owner)

- **Push every change.** After each fix, run exactly: `git add -A`, `git commit -m "What I changed"`, `git pull`, `git push`. Write a plain commit message saying what changed.
- **No the assistant attribution.** No `Co-Authored-By: the assistant` line in commits, and no "Generated with the coding assistant" line in PRs.
- **Ask the owner** whenever a fix needs a judgment call. This file marks those spots with **Ask first**.
- Before `git add -A`, run `git status` and make sure nothing private gets committed (`.env`, `.cache/`, local launch configs).
- Don't change rent, vacancy, eligibility or availability-review dates while fixing photos (see `data/README.md` → "Listing photos").

## How to run and test locally

```bash
python3 -m venv .venv && source .venv/bin/activate   # .venv already exists on the owner's Mac
pip install -r backend/requirements.txt
python backend/app.py                                 # serves http://localhost:8000
```

- Pages: `/` = about page (`frontend/about.html`), `/app` = tools page (`frontend/index.html`), `/resources` = programs page (`frontend/resources.html`).
- Tests: `python -m unittest discover -s backend -p 'test_*.py'` (78 tests; 77 pass without keys, see issue 6). Catalog check: `python backend/catalog.py --check` (expect "Catalog valid: 405 records").
- There is **no `.env`** on the owner's machine, so the Gemini and Google Maps features can't be tested end to end. Without keys they show "not set up" messages, which is correct. Don't create keys or put them in files yourself.
- **macOS quirk:** the the assistant desktop browser pane's launcher can't read `~/Documents` (macOS privacy), so `preview_start` with a launch config fails with `Operation not permitted`. Start the server from the shell in the background, then open `http://localhost:8000/app` with `preview_start` and a `url`.
- **zsh quirk when testing with curl:** pass headers inline, e.g. `-H 'Content-Type: application/json'`. A header kept in an unquoted shell variable is not split in zsh, so the server silently gets no JSON body.

---

## Issue 1: 19 listing photos fail to load, plus 1 wrong photo (biggest issue)

**What happens:** `/media/listings/<id>` returns **503** for 19 of the 279 listings that have a photo. When a photo fails, the card quietly drops to the no-photo style (`frontend/index.html`, the `image.addEventListener('error', …)` handler near line 655), so visitors see no broken image, just fewer photos.

**How the photo proxy works** (`backend/listing_photos.py`, `cached_photo`): it downloads only from hosts in `ALLOWED_HOSTS`, uses `requests` with its default User-Agent, sets **`allow_redirects=False`**, requires an `image/*` Content-Type, caps size at **`MAX_BYTES = 8 MB`**, checks the file with Pillow, and caches it in `.cache/listing-photos/`. A failure is remembered for 60 seconds (`_FAILURES`). The source code says on purpose: *"Do not bypass denied provider access."* **Don't** add a fake browser User-Agent or other ways around that without the owner's OK.

Photo metadata lives in **`data/resources.json`** (the catalog `load_catalog()` reads), and the review record is in **`data/photo_sources.json`**. Some URLs also appear in `data/candidates.json`. When a photo URL changes, update every file that has it (`grep -rn "<old url>" data backend`).

> **Testing tip:** request photos **one at a time, about 1.5 s apart**. Sending 8 at once got two working `ahcommunities.org` photos (Fort Henry Gardens, The Shelton) rate-limited, and the 60-second failure cache then made them look broken. Restart the server, or wait 60 s, to clear `_FAILURES` between attempts.

### 1a. Moved URLs (redirects): 3 listings. Fix these first.

The proxy refuses redirects, so each catalog URL must point at the final address.

| Listing id | Current `photo.url` | Redirects to |
|---|---|---|
| `nova-arlington-county-hunter-s-park-at-cherrydale` | `https://www.arlingtonva.us/files/sharedassets/public/housing/images/hunters-park-patio-ahc-inc.jpg?h=3456&w=5184` | `https://www.arlingtonva.us/files/sharedassets/public/v/2/housing/images/hunters-park-patio-ahc-inc.jpg?h=3456&w=5184` |
| `nova-fairfax-county-8421-broad` | `https://rent.brookfieldproperties.com/wp-content/uploads/2024/05/HDP_170731_19_FS_Web.jpg` | `https://lyvwellapartments.com/wp-content/uploads/2024/05/HDP_170731_19_FS_Web.jpg` |
| `nova-fairfax-county-the-parker` | `https://rent.brookfieldproperties.com/wp-content/uploads/2024/05/The-Parker_Ext_Building_LeasingOffice_Oct2015_Web.jpg` | `https://lyvwellapartments.com/wp-content/uploads/2024/05/The-Parker_Ext_Building_LeasingOffice_Oct2015_Web.jpg` |

Steps:
1. Hunter's Park is on the same allowed host (`www.arlingtonva.us`), so just update the URL.
2. For the two Brookfield listings, open the `photo.source_url` pages and confirm `lyvwellapartments.com` is the same property's official site (a rebrand or new operator), not some other company. If it is, add `lyvwellapartments.com` to `ALLOWED_HOSTS` and update both URLs. Also check whether the listing's `source_url` / `website` moved, and **ask first** before changing non-photo fields.
3. Check: `curl -s -o /dev/null -w '%{http_code} %{content_type}\n' http://localhost:8000/media/listings/<id>` should print `200 image/...`.

### 1b. Gone or empty sources: 2 listings

| Listing id | `photo.url` | What happens |
|---|---|---|
| `nova-alexandria-city-the-blake` | `https://www.theblakealexandria.com/wp-content/uploads/JPE_6717_1-1.jpg` | 404, the file is gone |
| `nova-alexandria-city-saint-james-plaza` | `https://www.huduser.gov/portal/sites/default/files/images/Edge-IP-1-102119.jpg` | 202 with an empty HTML body (bot check, not an image) |

Find a current official photo of the **same property** on its `photo.source_url` page or the provider's official site. Use a URL that is actually published there; don't guess or edit URL paths. Update `data/resources.json` and `data/photo_sources.json`, and add the host to `ALLOWED_HOSTS` if it's new. If no good official photo exists, remove the `photo` object from that record and add the community to `data/photo_review.json` with the reason. Wrong buildings, logos, floor plans and renderings are not acceptable (see `data/README.md`).

### 1c. Too large: 1 listing

`nova-alexandria-city-the-bloom-at-braddock`: `https://medialibrarycfo.entrata.com/101025/MLv3/3/21/2025/01/31/123802/679d2699c54211.70813974373.jpg` is a **9.4 MB, 4096×2925** JPEG, over the 8 MB cap.

**Ask first** which fix the owner wants:
- **(Recommended)** Use a smaller image that the provider actually publishes for the same photo (check `https://www.thebloomalexandria.com/`).
- Raise `MAX_BYTES`. That's simple, but it sends a 9 MB file to every visitor who sees this card's thumbnail.
- Have the proxy save a resized copy for display. That's a bigger change, and `data/README.md` says the cache keeps original bytes, so the docs would need updating too.

### 1d. Wrong image: 1 listing

`nova-prince-william-county-the-fitzgerald` loads, but `https://thefitzapts.com/wp-content/uploads/2024/03/Clubhouse.png` is a **64×64 PNG**, an icon, not a photo of the property. Replace it with a real exterior or community photo published on `https://thefitzapts.com/`, or remove the photo and log it in `photo_review.json`.

### 1e. Blocked by the provider (403 or dropped connection): 12 listings

These consistently return **403** (or the connection drops) to the server's requests:

- `www.communityhousingpartners.org`: `blacksburg-cedar-crest-apartments-1-3-bedroom-townhomes-confirm-rent`, `blacksburg-ellett-road-community-1-2-bedroom-community-confirm-eligibility`, `blacksburg-legacy-on-main-2-3-bedroom-community-confirm-rent`, `lindsay-hill-senior-apartments`
- `ahcommunities.org`: `key-gardens-one-bedroom`, `taylor-square-one-bedroom`, `the-ashtons-one-bedroom`, `the-macedonian-two-bedroom`, `westover-apartments-one-bedroom`
- `www.carmelpartners.com`: `nova-fairfax-county-the-avant-at-reston-town-center`
- `www.liveheming.com` (connection dropped): `nova-fairfax-county-the-heming`
- `thewaycroft.com` (connection error): `nova-arlington-county-the-waycroft`

A plain browser request to some of these returned 200 (for example `ahcommunities.org` and `liveheming.com`), so the sites seem to block non-browser clients or rate-limit.

1. First retest one at a time with a fresh server, since part of this may be rate limiting (see the testing tip above).
2. For what still fails, **ask first.** The code deliberately won't get around provider blocks. Options to offer the owner:
   - (a) leave them unavailable; the cards already fall back cleanly
   - (b) prefetch them on a network where they download (`python backend/listing_photos.py`, as `DEPLOY.md` already says to do before deploying) so the cache ships with the app
   - (c) ask the providers for permission or a direct image link
   - (d) change the request headers. Only do this with the owner's explicit yes, since it goes against the comment in the code.

### Checking the photo fixes

Run this with the server up. It fetches each photo one at a time, and every id should come back 200 with an image larger than 2 KB:

```bash
curl -s localhost:8000/api/listings > /tmp/listings.json
python3 - <<'EOF'
import json, time, urllib.request, urllib.parse
d = json.load(open('/tmp/listings.json'))
bad = []
for r in d['listings']:
    if not r.get('photo'):
        continue
    try:
        x = urllib.request.urlopen('http://localhost:8000/media/listings/' + urllib.parse.quote(r['id']), timeout=40)
        if not x.headers.get('Content-Type', '').startswith('image') or len(x.read()) < 2000:
            bad.append(r['id'])
    except Exception:
        bad.append(r['id'])
    time.sleep(1)
print(len(bad), 'failing:', bad)
EOF
```

Then run `python backend/catalog.py --check` and `python -m unittest discover -s backend -p 'test_listing_photos.py' -v` (it asserts every photo host is in `ALLOWED_HOSTS`). Update the photo counts in `data/README.md` → "Listing photos" if they change.

---

## Issue 2: about page scrolls sideways on phones

**What happens:** at 375 px wide, `/` has `scrollWidth` 387 against a 371 px viewport, so the page can be dragged left and right. The cause is in `frontend/about.html`, around lines 129–132: `.reveal.from-right { transform: translateX(32px); }` pushes the right-sliding feature cards (`<div class="feature reveal from-right">`, around line 253, and the hero `reveal from-right`, around line 224) past the right edge until they animate in. `/app` and `/resources` don't have this problem.

**Fix:** stop horizontal overflow on the about page without disabling the animation, for example add `html, body { overflow-x: clip; }` to its `<style>`. `clip` is better than `hidden` here because it doesn't create a scroll container. Don't remove the animation.

**Check:** at mobile width (375×812), on `/` run `document.documentElement.scrollWidth <= document.documentElement.clientWidth`. It should be `true` both before and after scrolling to the bottom. Check that the slide-in animation still plays and nothing visible gets cut off.

---

## Issue 3: resources chat says "call 211" twice

**What happens:** when the AI isn't available, `/resources` shows: *"The AI service isn't set up right now. Please try again in a few minutes, or call 211 for help. For urgent help, call 211."* The server message already ends with "call 211 for help", and `frontend/resources.html` line ~271 always adds more:

```js
addMessage('assistant', (err.message || 'We could not reach the assistant.') + ' For urgent help, call 211.', 'error');
```

**Fix:** add the 211 sentence only when the message doesn't already mention 211, e.g. `const msg = err.message || 'We could not reach the assistant.'; addMessage('assistant', /211/.test(msg) ? msg : msg + ' For urgent help, call 211.', 'error');`. Also check the home page chat in `frontend/index.html` (around line 1187, `botSay(... + ' For urgent help, call 211.')`) for the same doubling, and fix it there if it happens.

**Check:** without a Gemini key, click the "How do I qualify for Section 8?" example on `/resources`. "211" should appear only once.

---

## Issue 4: `/api/match` returns a vague 500 when the AI isn't set up

**What happens:** `POST /api/match` with `{"message":"I need a 2 bedroom in Fairfax under 1500"}` returns **500** "Something went wrong…", while `/api/ask` correctly returns **503** "The AI service isn't set up right now…". No page calls `/api/match` right now (`grep -rn "api/match" frontend` finds nothing), so this is low priority.

**Fix:** in `backend/app.py` → `match()` (near the end of the file), change `except Exception:` to `except Exception as error: return _gemma_error(error)`, which is the shared helper the chat routes already use.

**Check:** without a key, that request should return 503 with the "isn't set up" message. With a valid request and a key, the response should stay the same.

---

## Issue 5: no `.env`, so the AI and Maps features are untested

These features couldn't be checked end to end because no keys are set: the Gemma chat answers (`/api/ask`, `/api/ask/stream`), the web listing search (`/api/live-search`, which returns 502 without a key and shows "The web search didn't work this time"), and walking-distance search (`/api/housing/search`, `/api/housing/route`, `/api/place-photo`, which need `GOOGLE_MAPS_SERVER_API_KEY` / `GOOGLE_MAPS_BROWSER_API_KEY`). "Near me" on the map needs location permission and wasn't tested either.

**Don't** make keys or write them into files. **Ask the owner** to create `.env` from `.env.example` and fill in their keys, then test:
- the find form with "Near a supermarket": walk cards, the map and the list/map toggle on mobile
- the map's Blacksburg/Northern Virginia tabs and a typed area, which runs the web search, with orange "Found on the web, not checked" results
- the Ask Gemma chat on `/app` and the chat on `/resources`, including streaming
- `python backend/test_gemma.py`

Also consider improving the web-search message when the key is missing. Right now it says "didn't work this time. Please try again", which suggests a retry will help. A clearer message would say the service isn't set up, like the chat does.

---

## Issue 6: the test suite reports an error without a key

`backend/test_gemma.py` runs `raise SystemExit("Set GEMINI_API_KEY …")` when it's imported, so `python -m unittest discover -s backend -p 'test_*.py'` reports `ERROR: test_gemma` on any machine without a key (77/78). Make it skip instead of crashing discovery. For example, wrap the checks in a `unittest.TestCase` with `@unittest.skipUnless(os.getenv("GEMINI_API_KEY"), "needs GEMINI_API_KEY")`, while keeping `python backend/test_gemma.py` working as the README's quick key check (README line ~59). Afterwards a keyless run should show `OK (skipped=…)`.

---

## Suggested order

1. Issues 3, 4, 6 and 2 (small and safe; one commit each, push after each).
2. Issue 1a, then 1d, then 1b (data fixes).
3. **Ask first** about 1c and 1e.
4. Issue 5 once the owner adds keys.

## When you're done, report back

For each issue: what you changed (files and commits), how you verified it, and what's still open. For photos, list which ids now load, which you removed and logged in `photo_review.json`, and which are still blocked. Don't claim the site is fully working until the key-dependent features from issue 5 have been tested with real keys.
