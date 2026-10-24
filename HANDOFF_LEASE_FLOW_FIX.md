# Lease guide readability and completion flow

the assistant: Implement this user-requested improvement to **Your lease, step by step**. This is a handoff; the fix has not been implemented or browser-verified here.

## User feedback

The guide is hard to read. At the end of the five-step journey, **Prepare to sign** and **After signing** feel like they bounce between screens without a meaningful finish. The user wants a clear final screen, a downloadable checklist, and a small celebration after signing.

## Relevant starting point

Inspect `frontend/lease.html`, which currently contains the guide's markup, styles, and inline navigation logic. Trace `data-step`, `data-next`, `setStep`, `updateProgress`, and the final panel. The current markup includes a Prepare to sign button targeting index 3 and an After signing button targeting index 4. Reproduce the reported issue and determine whether navigation, completion state, unclear labels, or a combination causes the apparent loop. Do not assume the cause from the report alone.

## Requested changes

1. **Improve readability throughout the guide.** Use comfortably sized body text, strong contrast in light and dark modes, readable line lengths, clear headings, shorter plain-language instructions, and more space between tasks. Make the current step and primary next action obvious. Keep supporting explanations easy to access without overwhelming the main task. Check mobile layouts and browser zoom.
2. **Make the five-step journey coherent.** Each primary action should advance to the intended next stage. Back buttons should clearly indicate backward navigation. On step 5, provide an explicit finish action rather than sending users back into the signing preparation loop. Keep the progress indicator consistent with the actual current stage and checked tasks; distinguish reaching a step from completing it.
3. **Represent signing truthfully.** This app currently guides users to sign with the provider. Visiting a provider website or clicking After signing does not prove a lease was signed. Let users explicitly confirm that they finished signing with the provider before showing the signed completion state. If they have not signed, provide a clear way to resume signing preparation without trapping them in a loop. Do not require provider countersignature to be claimed if it is still pending.
4. **Add a dedicated final screen.** After the user's signing confirmation and finish action, show a clear, reassuring completion view, such as **You're ready for your next steps**. Show the selected property, completed tasks, and any remaining follow-up tasks. Make clear that completion refers to the user's guide/checklist and self-reported signing, not independently verified lease acceptance, approval, or guaranteed move-in readiness. Include useful next actions such as Download checklist, Review my steps, and Browse housing. Do not claim every task is complete if items remain unchecked.
5. **Provide a working checklist download.** Export a readable checklist using an approach suitable for this project, such as a text download or print-friendly document. Include the property name/address, the user's checked and unchecked tasks, and practical next steps: save the fully signed lease and addenda, obtain the provider's confirmation or countersigned copy, confirm any payment instructions and deadlines, arrange utilities if required, confirm move-in/key pickup, and document the unit's condition. Clearly distinguish completed items from pending ones. Do not include uploaded lease contents or sensitive financial information. The download must work, have a sensible filename, and reflect the current checklist state. If using print-to-PDF, label that action accurately rather than promising a direct PDF download.
6. **Add a restrained celebration.** A short confetti effect or small success animation should run once when the user explicitly finishes. Respect prefers-reduced-motion, keep controls usable, and provide an accessible static success message. Avoid replaying confetti when navigating back, revisiting, or downloading.
7. **Keep progress predictable.** Preserve checklist and completion state when moving between steps. If persisting progress across refresh, scope it to the selected property/floor plan and avoid storing lease text or other sensitive documents. Keep the existing reset behavior for a changed floor plan clear and consistent. A user must be able to review or correct answers after completion without losing progress unexpectedly.

## Acceptance criteria and validation

- Walk through all five steps in the browser: forward navigation works, back navigation is intentional, and the finish action reaches a real completion screen.
- Reproduce and resolve the reported Prepare to sign / After signing loop or confusing interaction; report its root cause.
- Test both a user who has signed and one who has not. No celebration or signed claim occurs merely from opening the provider website or visiting step 5.
- Verify the checklist download opens and matches the selected property and actual checked/unchecked state.
- Review the completed screen again and download again without replaying the celebration.
- Verify keyboard operation, visible focus, appropriate focus placement/announcement on step changes and completion, reduced-motion behavior, mobile readability, browser zoom, and light/dark contrast.
- Run the project's relevant checks and add focused regression coverage for navigation/completion behavior where appropriate. Summarize the implementation and validation, including any remaining limitations.

Keep this change focused on lease guide usability and completion; preserve existing document review and provider-link behavior except where the fix requires an adjustment.
