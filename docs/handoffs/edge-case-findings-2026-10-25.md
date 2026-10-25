# Handoff: additional edge-case findings

> **Status: done.** (1) A yearly budget becomes its monthly amount everywhere ($12,000 a year -> $1,000 a month, in follow-ups too); weekly amounts and incomes are not read as rent budgets. (2) What someone said no to does not count ("not a room, an entire apartment" is a whole place; naming both asks). Tests for 1 and 2 in backend/test_clarifier.py. (3) Lowest advertised rent keeps the API order exactly; in Availability first a photo only lifts a listing within its own availability run; Gemma and shared listings still lead. (4) Broken or old-format saved favorites are dropped and valid ones kept, so Favorites opens. 3 and 4 checked in the browser.

## Scope

Tested `ffefdfa` on October 25, 2026, in an isolated repository copy, using the local Gunicorn server and Chromium. No application code, catalog records, or review decisions were changed in the working checkout. This report requests fixes; it does not implement them.

The existing suite passes **196 tests**, but additional cases revealed four issues below. External AI/Maps credentials were omitted. Browser tests blocked external scripts and used a synthetic image response to keep photo metadata present without downloading provider assets. No production load or live AI-answer evaluation was performed.

## Previous findings: regression results

- `/api/options` rejects `rental_space: []` with JSON HTTP 400.
- `/api/housing/search` rejects `requiredAmenity: []` with JSON HTTP 400.
- `/api/options` rejects negative budgets and fractional household/bedroom counts with JSON HTTP 400 (five API regression cases passed).
- A delayed chat response no longer reappears after the find-form handler resets the conversation.
- Intro Skip navigation and chat HTTP-error recovery passed.
- Rapidly changing location from Blacksburg to Arlington retained the latest response, even when the Blacksburg response was delayed.
- A normal budget correction from $1,200 to $1,500 correctly updates the effective request.

The latest UI hides the older find form, so its reset regression was exercised by programmatically setting its location and submitting the existing handler. That is an internal regression check, not a claim that the form is currently exposed to users. Initial test selectors were updated for the new Filters & Favorites drawer; hidden-control timeouts were test-harness mismatches, not product bugs.

## 1. High priority: annual budget becomes a monthly budget in follow-ups

**Where:** `backend/clarifier.py`, `read_fields()`, stored budget answers, and `compose()`; inspect the shared budget parsing in `backend/advisor.py` too.

**Reproduction with `clarifier.resolve()` and one conversation state:**

1. “Find an entire one bedroom apartment in Blacksburg for $12,000 total a year.”
2. “Find an entire one bedroom apartment in Fairfax.”

The first request stores `budget: 12000`, without a time period. The follow-up becomes:

> Find an entire one bedroom apartment in Fairfax. My answers in this chat: under $12000 a month; the budget is the total for everyone who will live there.

The user explicitly supplied an annual amount, but the composed request says monthly. This changes the meaning of the affordability constraint by a factor of twelve. This was confirmed in deterministic request composition; no live model output was needed or tested.

**Requested fix:** retain the stated period, normalize clearly annual budgets to their monthly equivalent (here, $1,000/month), or ask a selectable clarification before using the number. An ambiguous period must not silently become monthly. Keep time period separate from per-person versus household-total basis. Inspect downstream filters so they receive the same normalized constraint the assistant describes.

**Acceptance:** annual, monthly, per-person, and household-total examples remain consistent across follow-ups and corrections. If weekly or shorthand amounts are unsupported, ask rather than guessing. Ordinary monthly amounts and comma-formatted amounts must keep working.

## 2. Medium priority: negated room preference overrides an explicit correction

**Where:** `backend/clarifier.py`, `read_fields()` and `_read_typed()`.

**Reproduction:**

1. “I need a room in Blacksburg under $1200.”
2. “I don't want a room; I need an entire apartment in Blacksburg under $1200.”

After the correction, `state['answers']['space']` remains **`room`**, not `entire_home`. No clarification question is produced. The original correction text is preserved, so the effective natural-language request and the structured answer disagree.

**Cause:** the parser sees the word “room” and applies the `ROOM` match before checking the explicit whole-home preference. It does not account for negation. This report confirms the wrong structured state; it does not claim a particular live AI recommendation was produced.

**Requested fix:** respect explicit positive corrections and avoid extracting preferences from negated phrases. When a statement is genuinely ambiguous, ask the user which rental space they mean instead of silently choosing one. Make sure stale state is not added back to a later request.

**Acceptance:** test “not a room, an entire apartment,” “not a whole apartment, just a room,” and equivalent corrections during an open question and after a complete search. Preserve normal room/whole-home matches and the user's option to choose either.

## 3. Medium priority: photo-first ordering defeats Lowest advertised rent

**Where:** `frontend/index.html`, `renderHousing()` and its `ordered` comparator.

With **Lowest advertised rent** selected, the API returns the correct ascending sequence, but the UI moves entries with photos ahead of entries without photos before taking the first six cards.

**Observed first six monthly prices:**

| API rent order | Displayed cards |
| --- | --- |
| $495 | $495 |
| $550 | $555 |
| $555 | $565 |
| $565 | $865 |
| $570 | $1,036.79 |
| $675 | $1,069 |

For example, the $550 listing at 1203 North Main is omitted from the initial cards while $1,069 is shown. Checking only whether the visible six happen to be ascending misses this problem; compare the displayed prefix against the full API sort order.

**Requested fix:** honor the selected price/availability order before photo preference. Photos can break otherwise equivalent ties in an appropriate default mode, but must not hide cheaper matches beneath more expensive entries when price sorting is selected. Preserve explicit Gemma ranking and shared-listing highlighting deliberately; define any pinned exception clearly rather than letting competing sorts silently override one another.

**Acceptance:** for a mixed photo/no-photo fixture with distinct rents, the first six displayed records equal the first six correctly sorted records. Verify Show More/Show All and another sort mode. Do not solve this by removing valid listings without images.

## 4. Medium priority: malformed saved records crash Favorites

**Where:** `frontend/index.html`, initialization from `clearhome.favorites`, `shownRows()`, and `renderHousing()`.

In a browser on the site's origin, seed local storage with either valid JSON value:

```js
localStorage.setItem('clearhome.favorites', '{"bad":null}');
// Or:
localStorage.setItem('clearhome.favorites', '{"bad":{"id":"bad","floor_plans":"old-format"}}');
```

Reload `/app`, open **Filters & Favorites**, then select **Favorites**.

- The null entry produces `Cannot read properties of null (reading 'floor_plans')`.
- The malformed floor-plan entry produces `plans.map is not a function`.

The JSON parsing catch does not protect against valid JSON with invalid record shapes. This is a local-storage corruption/migration edge case, not an attack that was shown to affect other users.

**Requested fix:** validate the top-level storage value and each saved record before rendering. Safely discard unusable entries, preserve valid favorites, normalize supported older shapes, and show a usable empty/recovery state if nothing remains. Keep storage-denied/quota behavior nonfatal. Do not execute markup from stored values.

**Acceptance:** test malformed JSON, null/primitive/array top-level values, null entries, invalid `floor_plans`, mixed valid/invalid records, and saving/removing after recovery. No uncaught exception or stuck listing grid should result.

## Evidence and limits

Evidence is in `/workspace/scratch/edge-cases-2026-10-25/`: `prior-regressions.json`, `chat-parsing.json`, `chat-follow-ups.json`, `rent-order.json`, `new-browser-edges.json`, and `browser-targeted.json`. These workspace artifacts may not exist on another machine; use the portable reproductions above. The browser checks produced four passing prior-regression cases plus a passing rapid-filter case, and three failing assertions covering the sort issue and both malformed-favorite variants. The two chat findings were inspected directly in parser/state outputs.

Actual Maps rendering, provider imagery, production capacity, live AI quality, and broader browser/device coverage remain unverified. Unsupported `$1.2k` input prompted a budget clarification rather than guessing; conflicting Blacksburg/Arlington input prompted an area clarification. Do not count those cautious responses as defects.

## Delivery instructions

Inspect current `main`, reproduce the issues, and add focused regression tests with each fix. Preserve teammate changes and existing safety/clarification behavior. Verify the state transitions and rendered listing order, not only syntax or response status.

Follow the user's workflow: `git add -A`, `git commit -m "Describe the fixes"`, `git pull --rebase origin main`, then `git push origin main`. Resolve conflicts and rerun affected checks. Stay on `main`. Report implementation commits and checks; do not mark these findings fixed until the implementation is tested.
