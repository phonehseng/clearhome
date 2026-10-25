# Handoff: selectable clarification questions inside Gemma chat

## Status: implemented

- `backend/clarifier.py` decides when to ask (a script, no AI), validates every field and value the page sends back, and writes answers into the request (newer answers win; Skip and Not sure stay unknown). Up to three questions per request.
- `backend/app.py`: the `/app` chat sends `chat` (its state) and `reply` (a button answer); the stream adds `state` and `question` events. Pages that send no `chat` (resources page) work as before. A stale or invalid reply gets 409 or 400.
- `frontend/index.html`: questions render as a fieldset inside Gemma's bubble (buttons, or ticks plus Continue), with Not sure, Skip and Type My Own Answer; the text box stays usable; a find-form search resets the chat and its answers.
- Other modules can ask with `clarifier.question(field, text, choices)` (a `place` field is registered for "which store or city?" questions).
- Tests: `backend/test_clarifier.py`.

## User request

When the user has not provided enough information, Gemma should ask a follow-up question inside the chat instead of assuming their needs. Embed selectable answers or a compact questionnaire directly in Gemma's message. Use the user's answers to continue the same conversation and produce better grounded recommendations.

This file is a handoff, not an implementation. The user currently requests Markdown instructions rather than direct application changes.

## Desired experience

- Start with the user's actual message and relevant information they explicitly supplied earlier in this conversation or the search form. Identify which missing detail would materially change the next answer.
- Ask one focused question at a time by default. A small group of two or three related fields is acceptable when that is easier to answer; do not open with a long mandatory form.
- Render the question and answer controls inside an assistant chat bubble, matching the existing glass/chat styling. Keep the normal text composer available.
- Use short, context-specific answer buttons, radio choices, or checkboxes. Include an escape route such as **Not sure**, **No preference**, **Skip**, or a custom typed response where appropriate. Do not preselect an answer or submit a default on the user's behalf.
- Selecting a single answer should submit that choice once, display a readable user reply in the transcript, and continue the conversation. For multiple selections or grouped fields, provide an explicit Continue button.
- Remember confirmed answers for this conversation, avoid asking again, and let users correct earlier choices. Do not silently reset them when a later message omits the same details.
- If the user skips a question, keep the value unknown or explicitly unconstrained and explain any resulting limitation. Do not replace the skipped answer with a guessed need.

## Example flow

User: “I need somewhere to live.”

Gemma: “What kind of help do you need first?”

**Find a rental** · **Somewhere safe tonight** · **Help paying rent** · **Not sure**

If the user chooses Find a rental, ask for the area next. Offer supported locations and let them type another place. Then ask for monthly housing budget if it is still unknown, with a clear distinction between rent-only and total housing costs if relevant. Only ask about rooms versus an entire home, bedrooms, move-in timing, or accessibility when those details affect the request.

If the user already says “An entire one-bedroom home in Blacksburg under $1,200 a month,” do not ask for location, rental type, bedrooms, or budget again. Proceed with the known constraints or clarify a genuinely unresolved detail.

## When to clarify and when to answer

- Clarify missing or conflicting facts that would substantially change the recommendation: location, type of help, budget, rental space, or urgency. If the user changes a stated constraint, use the correction.
- Do not infer income, age, disability, household composition, student status, homelessness, or program eligibility from a name, location, writing style, or silence. Ask only for relevant information; offer broad guidance without requiring unnecessary sensitive details.
- General factual questions, such as “What is a housing voucher?”, should receive an answer without an unrelated housing questionnaire.
- Urgent safety or shelter requests should receive immediate, relevant emergency/intake guidance alongside any essential follow-up. Do not delay help behind a budget form or assume that an unconfirmed shelter has a bed available.
- Distinguish a search preference from confirmed eligibility. User answers do not establish a program's approval or a property's availability.
- Asking a question is not performing a search. Avoid showing personalized cards or moving the map based on guessed values while clarification is pending. If broad results are useful, label them clearly as broad results.

## Implementation guidance

- Inspect the latest `frontend/index.html` chat renderer, `ask()`, streaming/event handling, message history, existing starter chips, and the first-question handoff from the homepage.
- Inspect `backend/app.py`, `backend/advisor.py`, `backend/prompt_tools.py`, and any newer chat/profile code. Apply clarification before filtering listings or drafting a personalized answer. Updating prompt wording alone is insufficient if downstream code still applies guessed defaults.
- Add or extend a structured clarification response/event alongside the existing chat protocol. Include a stable question ID, the missing field, question text, choice IDs/labels, selection mode, and whether skipping or custom input is supported. Do not render model-generated HTML or infer interactive controls by scraping prose.
- Validate supported fields and answer values on the backend. Treat selected answers and custom text as user input, not as trusted instructions. Do not allow arbitrary model-generated field names or choices to mutate server state.
- Merge confirmed answers with conversation state using clear precedence: a newer explicit correction overrides an older answer. Keep unanswered values distinct from false, zero, and No preference.
- Send only the relevant conversation context needed to interpret the answer. Keep this state within the conversation; do not add accounts, persistent sensitive profiles, or new logging of personal information for this feature.
- Prevent double submission and stale-question responses from changing the latest conversation state. Mark answered questions as answered, preserve the selected label in the transcript, and provide a retry path if submission fails.
- Use native accessible controls, visible focus states, labeled groups, keyboard support, and comfortable mobile touch targets. Announce the new question politely without repeatedly stealing focus or auto-scrolling away from what the user is reading.
- Preserve existing streaming responses, source grounding, search filters, map behavior, chat reset, and the first question passed from the Gemma introduction. Reset should clear pending questions and confirmed conversation answers as well as the transcript.

## Acceptance checks

- Vague request produces a relevant embedded question with working answer controls instead of assumed filters.
- A sufficiently detailed request goes directly to an answer/search without repeating supplied details.
- A selected answer, custom typed answer, Skip, and Not sure each continue the same conversation correctly; unknown values stay unknown.
- Corrections override prior answers, and conflicting constraints trigger clarification rather than silent assumptions.
- Multi-select/grouped questions submit only after Continue. Repeated clicks and answers to stale questions do not create duplicate searches or overwrite newer state.
- General informational questions and urgent shelter requests are handled appropriately without unnecessary mandatory questionnaires.
- Network failure, malformed clarification data, chat reset, streaming, and homepage first-question transfer remain usable.
- Verify desktop, mobile, keyboard navigation, and screen-reader labeling in a browser. Add meaningful backend/protocol checks for clarification decisions and state merging; report checks actually run.

## Delivery

Implement on the latest `main`, preserving teammates' work. Follow the user's sequence: `git add -A`, `git commit -m "Describe the change"`, `git pull --rebase origin main`, then `git push origin main`. Resolve conflicts and rerun affected checks. Report the implementation commit and limitations. Do not create a fix branch or mark this handoff implemented before the feature is built and verified.
