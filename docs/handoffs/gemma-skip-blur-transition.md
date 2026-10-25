# Handoff: blur transition when skipping Gemma

> **Status: done** in 208f705, for both Skip and a first question: the card blurs away on the intro's blue and the tools page clears in from the same blue, with a one-use marker read before first paint (no replay on reload, direct visits or back/forward).

## Request

When a user opens the Gemma 4 introduction and selects **Skip**, transition smoothly to the main tools page (`/app`). The destination currently appears abruptly. Blur and fade out the introduction, then reveal the tools page through a blur that gradually clears. Make this feel like one continuous transition, without a flash of the homepage between screens.

This file is an implementation request, not an implemented change. The user requested Markdown handoffs instead of direct application edits. The earlier blur-transition implementation was reverted; inspect the latest code and implement this request deliberately rather than restoring that commit wholesale.

## Where to look

- `frontend/about.html`: the `#start` dialog, `.start-card`, `.start-skip`, `.start.leaving`, and the final script that opens the introduction and handles its form submission.
- The Skip control currently links directly to `/app`. It has no animated exit handler.
- `frontend/index.html`: the destination tools page. An exit animation on the homepage alone cannot prevent an abrupt appearance after navigation; the arrival needs to participate too.

Confirm these details against the latest `main` before editing. Preserve concurrent teammate changes.

## Desired behavior

1. On an ordinary Skip click or keyboard activation, fade and blur the Gemma card out over approximately 200–300 ms. Keep the surrounding background covered throughout the handoff.
2. Navigate to `/app` once. Its first visible frame should already have the transition treatment applied; do not briefly display the sharp page and add blur afterward.
3. Reveal the actual tools page by fading away a subtle overlay and clearing its blur over approximately 450–700 ms. Match the existing blue/glass palette and avoid a white flash, layout movement, or an unnecessary loading screen.
4. Finish with the normal, sharp, fully interactive page. Remove temporary classes, overlays, timers, and transition state. Do not leave an invisible layer intercepting clicks or focus.

These timings are starting points; tune them by viewing the actual transition on desktop and mobile. Keep the effect brief and restrained.

## Implementation constraints

- Scope this change to **Skip**. Preserve first-question submission and the `ch:first-question` handoff; changing the send flow is not required.
- Preserve the anchor's real `/app` destination and native modified-click/new-tab behavior. Without JavaScript or animation support, Skip must still work.
- Coordinate departure and arrival across the two documents. A short-lived, one-use session marker is an option: set it for the Skip navigation, consume it before the destination's first paint, and reject stale values. Handle unavailable storage without blocking navigation.
- Direct visits to `/app`, reloads, and back/forward navigation must not replay a stale entry effect.
- Prevent repeated activation from scheduling multiple navigations. Do not dismiss the dialog early and expose the homepage underneath.
- Respect `prefers-reduced-motion`: skip the blur/movement and navigate promptly. Provide a simple fade or immediate navigation when backdrop blur is unsupported.
- Make cleanup reliable if an animation event does not fire. Avoid requiring an API response, map load, font download, or AI response before navigating or completing the transition.
- Keep existing keyboard navigation, focus visibility, and screen-reader behavior usable. Do not add an artificial announcement for a purely decorative effect.
- Leave application logic, housing data, and unrelated layouts unchanged.

## Acceptance checks

- Desktop and mobile: open the introduction, select Skip, and observe a continuous blur/fade into `/app`, with no sharp-page pop or homepage flash.
- Keyboard: activate Skip with Enter and confirm the same outcome; verify focus and controls work afterward.
- Repeated Skip activation: only one navigation occurs.
- Reduced motion: navigation remains prompt and no blur/movement animation runs.
- Open Skip in a new tab, visit `/app` directly, reload, and use browser back/forward: no unwanted entry replay.
- Storage unavailable and slow navigation: the destination remains reachable, and no overlay becomes stuck.
- Submit a first question: existing transfer and submission behavior still works.
- Use a real browser to check both sides of navigation, including the destination's first frame and the removal of the overlay. Report which checks ran; do not claim the transition is verified from CSS inspection alone.

## Delivery

Implement on `main`. Follow the user's workflow: `git add -A`, `git commit -m "Describe the change"`, `git pull --rebase origin main`, then `git push origin main`. Resolve conflicts while preserving teammates' work and rerun affected checks if integration changes the transition. Report the commit hash and any remaining limitations. Do not create a fix branch for this request.
