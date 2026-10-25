# Handoff: fix housing intent and multi-constraint chat answers

Please investigate and implement this high-impact Gemma chat correction, validate it end to end, and commit and push the actual fix. Thank you for the work on the existing experience; this request focuses on making its answers reliably address what people ask.

## Exact reproduction from the user

User message:

> i need something close to campus under 1000 and they need accessable with pets and is a 2 person

The screenshot's response ignores those constraints and starts with **I have received the list of resources for Northern Virginia and Arlington County**, asks the user to explain what they want again, and presents sample questions about emergency shelter, cold-weather help, and legal aid. The visible screenshot is a generic shelter/services introduction, not a relevant housing answer. The user also reports unwanted helpline detours. Do not describe the screenshot as showing a suicide hotline; it does not establish that.

## Investigate the full pipeline

- Trace the user message through frontend request construction, conversation history, intent/routing rules, structured extraction, catalog filtering/retrieval, prompt/message roles, model invocation, response validation, streaming, and fallbacks.
- Verify the actual latest user message reaches the answering model and is not replaced by resource context, an onboarding prompt, or a stale conversation turn. Determine why resource-list acknowledgment/sample questions appear instead of an answer. Do not assume model intelligence or timeout is the root cause.
- Inspect whether default geography, keyword prefilters, candidate truncation, missing schema fields, or fallback logic silently route ordinary rental searches into shelter resources or discard constraints.

## Required behavior

1. Recognize the example as a **rental housing search** despite typos. Extract and preserve: near campus, budget below $1,000, accessibility need, pets, and household size of two. Distinguish household size from bedroom count. Do not infer two bedrooms, a particular disability, pet type, campus, city, or whether the budget is total versus per person.
2. Use explicit location/campus context already supplied by the user or selected form/map when appropriate, with clear precedence for the latest explicit message. If campus remains ambiguous, ask **Which campus or city?** If budget basis matters, clarify **Is $1,000 your total monthly budget or per person?** Keep follow-up questions concise and retain all known preferences. Do not make the user restate everything.
3. Support general housing parameters consistently: location/landmark and walking/commute preference, budget and price basis, household size, bedrooms/room versus whole unit, pets, accessibility, and timing when provided. Ask about specific accessibility features or pet details only when needed to refine matching; do not ask intrusive questions.
4. Filter/rank using supported facts and preserve hard constraints. Use verified listing attributes for pet policies, occupancy, accessibility, prices, and proximity. Unknown is not yes: distinguish **verified matches**, **possible options needing confirmation**, and **no verified matches**. Never invent wheelchair access, pet permission, room capacity, current vacancy, or a walking time. Distinguish pets from assistance-animal accommodations; do not assume a no-pets listing settles accommodation eligibility.
5. Do not silently relax budget, location, pet, or accessibility requirements. Explain any proposed broader search and let the user choose. Distinguish per-person room prices from whole-home rent and account for known fees without fabricating totals.
6. Answer with a brief acknowledgment of the actual requirements, relevant evidence-backed options when available, and a clear next step. If there is insufficient location information, ask the needed question rather than fabricating local listings. Avoid generic introductions, sample question menus, unrelated legal-aid lists, or shelter/helpline referrals for an ordinary rental search. Preserve appropriate emergency routing when the user actually requests emergency shelter or expresses a relevant crisis.
7. Maintain constraints across follow-ups such as **Virginia Tech**, **total for both of us**, **a cat**, or **15 minutes walking**. Explicit corrections replace earlier preferences. Do not allow a prior shelter discussion to override a later explicit rental search.

## Model time and complexity

The user suggests more thinking time for complex prompts. Inspect the deployed model's actual capabilities/settings and current time, output, and context limits. Evaluate routing/extraction correctness first; longer inference alone will not repair missing user messages or wrong candidates. If measured truncation or timeouts cause this failure, adjust appropriate supported limits for multi-constraint questions, retaining useful streaming/loading feedback, cancellation, and bounded latency. Never display hidden reasoning. Log enough non-sensitive diagnostics to distinguish routing, extraction, retrieval, model, and fallback failures without retaining unnecessary personal details. Explain any changes with evidence rather than promising a larger timeout fixes intelligence.

## Regression and end-to-end validation

- Replay the exact typo-filled prompt. With no campus context, it should retain all requirements and ask for the campus/budget clarification, not return the generic services introduction. With an explicit campus and budget basis, search the right housing records.
- Cover pets/accessibility/household-size combinations, per-person versus total rent, unknown policy attributes, no matching inventory, follow-up corrections, larger prompts, model failure/timeout, and ordinary rental queries following a shelter conversation.
- Verify genuine **I need a shelter tonight** queries still receive appropriate shelter intake help. This fix must improve intent discrimination rather than remove emergency assistance globally.
- Add focused meaningful regression tests for extraction/routing/filtering, and exercise the real chat endpoint and streamed UI. Verify grounded answers against actual returned records; mocks alone do not establish answer quality.
- Report root cause, implementation changes, representative before/after behavior, tests and runtime checks, remaining data/model limitations, and the implementation commit hash. State if deployment remains outstanding.

This file is the user-requested implementation handoff, not a claim that the issue is fixed. Inspect current repository instructions and concurrent changes before editing.
