# Handoff: make homes-near-a-place answers geographically correct

> **Status: done** in c47de59 (pushed to main, not deployed yet). Root cause: a lowercase store name wasn't read as a place by any of the instant answers, so "give me something close to walmart" went to Gemma with 12 generic Northern Virginia listings (a capitalized "Walmart" would have gone to one random branch ranked by straight-line distance). Now `backend/near_place.py` reads store chains (Wal-Mart, wallmart and other typos; Target, Kroger, Food Lion and more) and other "close to" places. It asks "Which Walmart, or which city?" (and whether a 10–15 minute walk is what close means) when no town is known from the question, the find form or the chat, finds the real stores with Google Places, and lists only homes whose Google walking route (or a drive or bus trip, when they say so) fits the stated time or a stated 15-minute default. Homes Google can't route, and long walks, are never called close. Questions with pets or similar needs go to Gemma with only the measured homes, and cards get a Directions link to the same store. Tests: `backend/test_near_place.py`. Live-checked: Blacksburg (Walmart: the Christiansburg store, nothing within 15 minutes, closest a 20-minute walk; Kroger: 4 homes; the real Gemma path with pets) and Northern Virginia (Target in Arlington: 12 homes; the Walmarts on Richmond Hwy: 2; Inova Fairfax and George Mason: none on foot, drive options labeled), plus the browser chat. Limits: up to 3 stores and 25 routed homes per answer; route times don't confirm sidewalks or step-free access; Gemma's settings are unchanged (this was routing and grounding, and no model was trained).

Implement, validate end to end, commit, and push a real fix for Gemma's place-based housing search. Coordinate with the earlier housing-intent handoff; inspect current code and deployment before editing.

## Reproduction and failure

Exact user message: **give me something close to walmart**.

The screenshot shows a generic Northern Virginia apartment summary sorted/grouped by rental category rather than an answer tied to a Walmart location. The user reports that the top result is roughly a two-hour walk away. That route duration is user-reported, not independently verified in this handoff. A two-hour walk must not be presented as a close walking match. The user wants practical proximity for people with limited walking tolerance, including older adults.

## Investigate and correct the pipeline

- Trace frontend message/context, intent extraction, place resolution, candidate retrieval, routes, ranking, prompt construction, streamed response, result cards, and fallback behavior. Find why the query became an unfiltered rental summary. Confirm that deterministic catalog shortcuts and failure fallbacks honor the same proximity constraints as model-generated answers.
- Recognize brand/store names, addresses, campuses, employers, landmarks, and ordinary variations such as **near Walmart**, **close to Wal-Mart**, **walking distance from the Walmart on [street]**, and follow-ups like **that store**. Do not hardcode Walmart as the only supported brand.
- Resolve the requested destination through the existing supported Places/geocoding service, using explicit city/address first and relevant selected area/conversation context second. A chain name is not a unique place. If multiple plausible branches remain, ask a short question or offer a small set of real branches with city/address. If no area is known, ask **Which Walmart or which city?** Never silently default to Arlington, Northern Virginia, or a random branch.
- Distinguish a requested specific branch from **any Walmart near homes in Blacksburg**. For the latter, search relevant real branches within the selected area and match homes to the nearest suitable branch. Deduplicate results, label each destination, and keep requests bounded/cached where appropriate.

## Proximity and constraints

1. Establish mode and tolerance. Preserve any explicit walk/drive/transit time. If the user only says **close**, ask a concise clarification such as **Which Walmart, and is a 10–15 minute walk what you mean by close?** Use an explicitly stated default only when context makes that sensible, and make it visible. Do not silently assume a universal definition of close.
2. Use real walking-route distance/time for walking claims; straight-line distance is only a candidate prefilter and must not be labeled a verified walk. Calculate toward a verified public destination/entrance where supported, not arbitrary property centroids with false precision. Rank qualifying candidates by route time with a stable tie-breaker, preserving other user constraints.
3. Enforce the requested maximum as a constraint. A two-hour route cannot appear as a match to a short walk, even if it is the cheapest listing or first catalog entry. If no verified listings qualify, say so and offer clearly labeled broader alternatives. Never silently widen the threshold or replace destination-specific results with a generic list.
4. Keep budget/price basis, household size, pets, accessibility, rental type, and timing across follow-ups. Do not infer that an older person qualifies for a property or can traverse a route. Published route time does not verify sidewalks, step-free access, safe crossings, weather suitability, or a person's walking speed. Mention route accessibility uncertainty briefly when relevant and ask about required features without medical assumptions.
5. Missing geocodes, unavailable route services, route errors, and zero-route results must produce clear uncertainty or a useful clarification. Unknown routes must never receive zero-minute scores or proximity badges. Do not describe cached/hypothetical times as freshly verified.

## Answer and UI

- Begin with the resolved store name/address and the applied travel criterion, then show a small number of verified relevant homes with actual route time/distance, rent basis, source, and directions to the same resolved destination.
- Keep map pins, result-card order, directions links, and textual recommendations aligned. Ensure the prose cannot recommend unsupported listings outside the routed result set or drop the requested place.
- Avoid the generic **Here is a summary of available apartment listings in Northern Virginia** response. Do not claim current vacancy merely because a catalog record exists.
- Ask for clarification before paying for unnecessary broad route batches. Stream concise progress such as finding the store or checking walking routes, with cancellation and bounded request timeouts.

## Model reasoning/runtime

The user asks for more thinking/training. Treat this primarily as a measurable routing, grounding, and tool-use issue. Inspect the deployed model's supported settings and actual truncation/timeout behavior. Increase appropriate context/output/time budgets for complex multi-constraint requests only if evidence supports it; maintain bounded latency and cancellation. Do not claim model training occurred from changing a prompt or timeout. Actual fine-tuning is outside this request unless separately justified and authorized. Never display hidden chain-of-thought; show useful search progress and concise explanations instead.

## Validation and deliverable

- Regression-test ambiguous Walmart with no location; a named branch; multiple branches in a selected city; any nearby branch; misspellings; campus/employer destinations; mode/time changes; and multi-turn constraint retention.
- Include route fixtures where a cheap two-hour-walk listing must lose to a qualifying nearby listing, plus no matches, failed routes, unknown coordinates, and explicit thresholds. Verify all response paths and fallbacks respect constraints.
- Exercise the real endpoint and browser against actual place/route data for representative Blacksburg and Northern Virginia searches. Report which branch, threshold, candidate count, and route outcomes were used. Do not invent successful live checks when credentials or services are unavailable.
- Report root cause, changes, tests/live checks, remaining limitations, and the implementation commit hash. Commit and push the actual implementation; this handoff alone does not satisfy the request. State whether the fix is deployed and verified on the live site.
