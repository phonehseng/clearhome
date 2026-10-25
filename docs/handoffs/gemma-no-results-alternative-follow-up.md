# Handoff: offer a next search when Gemma finds no matches

## User request

When Gemma searches using the user's criteria and finds nothing, it should not stop with a no-results message. Clearly explain that no matching results were found, then ask a useful follow-up question about the next best alternative search criteria. Let the user choose an answer inside the chat and continue the search in the same conversation.

This is a Markdown handoff only. Application code has not been changed by this request.

## Desired experience

1. Complete the original search using the user's confirmed criteria.
2. If it succeeds but returns zero matching results, acknowledge that plainly: **“I couldn’t find reviewed listings matching those requirements in our current catalog.”** Briefly restate the important constraints so the user can see what was searched.
3. Ask one focused question proposing the most useful next step. Embed selectable answers in the same assistant reply, using the existing chat-question UI. Keep custom typed responses available.
4. Wait for the user's choice before changing a constraint or running an alternative search. Reflect the chosen change in the transcript and preserve everything else.
5. Search again and explain which criterion changed. Label alternative or partially confirmed results honestly; do not present them as exact matches to the original request.

The wording should describe the scope of our data, not claim that no suitable housing exists anywhere. A failed catalog match is not proof that there are no homes or vacancies in that area.

## Example

User: “An entire one-bedroom apartment in Blacksburg under $700 a month.”

Gemma: “I couldn’t find reviewed listings for an entire one-bedroom apartment in Blacksburg at or below $700/month. Would you like to keep that budget and explore a different option?”

Possible answer controls, **only when supported by the actual search evidence**:

- **Explore nearby supported areas** — retain the budget, bedroom count, and whole-home requirement; ask which area if needed.
- **Consider a room in shared housing** — retain the location and budget, but explicitly ask permission to change the rental space. Do not imply a room provides the privacy or occupancy capacity of an entire home.
- **Change my budget** — ask for a new maximum, without selecting or raising it automatically.
- **Keep my requirements** — retain the constraints and explain other useful next steps, such as assistance programs or contacting providers about unconfirmed details.

Do not hardcode these options for every search or imply any will produce a match without evidence. If only one relevant alternative is supported, offer that focused question instead of a generic menu.

## Choose alternatives from evidence

- Use deterministic searches or counts against the current eligible catalog to identify which user-approved change could actually help. Prefer a small, understandable change over discarding several requirements at once.
- Suggest changing one criterion at a time: location, budget, rental space, bedrooms, move-in timing, or walking distance, as relevant. Respect any criterion the user has stated is nonnegotiable.
- A numeric suggestion such as a higher budget or longer walking time must come from available source-backed prices or measured routes, with units clear. Do not invent thresholds, counts, travel times, availability, or affordability.
- Never change monthly versus annual amounts, per-person versus whole-home prices, accessibility requirements, or program eligibility silently. Do not suggest a higher rent as the default answer to someone who says they cannot afford it.
- Missing rent, eligibility, accessibility evidence, or availability is **unknown**, not a confirmed match or a reason to claim a property definitely fails. If the user asks to see possible matches, separate those from confirmed matches and explain what must be checked.
- Do not relax safety constraints, revive closed/unverified/hidden entries, or describe waitlists as available homes. Geographic alternatives must stay within supported coverage or clearly explain the coverage limit.

## Conversation and protocol requirements

- Build on `docs/handoffs/gemma-chat-follow-up-questions.md` and inspect the latest implemented behavior in `backend/clarifier.py`, `backend/advisor.py`, `backend/app.py`, `backend/near_place.py`, and the chat renderer in `frontend/index.html`. Also inspect other search paths that can produce empty results, including walking-distance searches.
- Trigger this flow from the actual search outcome, not by parsing a model's prose for phrases like “no results.” A request that still needs clarification is different from a completed search with zero matches.
- Distinguish a genuine empty result from provider outages, timeouts, missing credentials, malformed requests, or unavailable data. An operational failure should offer retry/recovery and must not claim the user's criteria produced no matches.
- Reuse or extend the structured question/event protocol so the answer controls carry stable question and choice IDs and backend-validated actions. Do not render model-generated HTML or allow arbitrary field changes from unchecked choice data.
- Remember the original criteria, completed attempts, pending question, and explicitly accepted changes within the conversation. A custom typed correction must work as well as a selected button. Preserve the existing privacy model; do not introduce persistent personal profiles.
- Invalidate old questions when the user changes the request, prevent duplicate submissions, and preserve the recent fixes for cancellation/reset races. An answer to an obsolete alternative question must not overwrite a newer request.
- Avoid a loop of the same unsuccessful suggestions. After an unsuccessful alternative, acknowledge what was tried and ask about another relevant untried change, or offer practical assistance/contact next steps. Respect “Keep my requirements,” Skip, and Not sure without guessing a replacement value.
- If an alternative truly has no useful support in the catalog, say so. Do not fabricate an option just to keep the conversation moving.

## Safety, accessibility, and scope

- For urgent shelter or safety requests, provide immediate appropriate help/intake guidance alongside the next-step question. Do not put emergency guidance behind several rounds of preference questions or suggest a paid hotel meets a zero-cost shelter requirement.
- Keep controls keyboard accessible, labeled, readable on mobile, and announced appropriately when added to the conversation. Preserve the ordinary composer and visible focus.
- Keep existing search filters, map, listing source links, and result cards consistent with the accepted search criteria. Do not change unrelated page layouts or housing data to make an empty search look successful.
- Do not offer notifications, future vacancy alerts, or provider contact as automated actions unless those capabilities actually exist. Contact suggestions can link to verified provider information for the user to act on.

## Acceptance checks

- A completed zero-match search produces both an honest scope-limited explanation and an actionable embedded follow-up.
- An exact-match search follows the normal result flow, without unnecessary relaxation questions.
- Selecting an alternative changes only the approved criterion and searches again; original nonnegotiable constraints remain intact.
- Unsupported choices and stale question IDs are rejected safely. Repeated clicks do not create duplicate searches.
- A custom typed answer, Keep my requirements, Skip, Not sure, and a change of topic each behave sensibly.
- A failed alternative does not repeat the same question indefinitely. Do not promise results when none have been established.
- Timeouts/provider errors offer recovery rather than a misleading no-matches claim.
- Annual/monthly budgets, shared-room pricing, unknown property facts, accessibility needs, and urgent shelter cases are handled truthfully.
- Test backend outcome/state transitions and browser rendering/selection on desktop, mobile, and keyboard. Preserve existing streaming, first-question transfer, and reset/error recovery checks. Report checks actually run.

## Delivery

Implement on the latest `main`, preserving teammate changes. Follow the user's workflow: `git add -A`, `git commit -m "Describe the change"`, `git pull --rebase origin main`, then `git push origin main`. Resolve conflicts and rerun affected checks. Do not create a fix branch. Report the implementation commit and limitations; do not mark this handoff implemented until the behavior is built and tested.
