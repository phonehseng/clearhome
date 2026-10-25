# Handoff: green bird perched on the homepage headline

> **Status: built, then removed.** aaf65fd added the perched bird (later restyled to match the flock, in orange); 5edcca8 removed it at the user's request.

## User request

Add a small green bird, visually matching the birds already flying on the site, perched on the **top-left of the F** in **“Find Your Way Home.”** on the main homepage. When the cursor hovers over the bird, it should take off and fly away.

This Markdown file is the requested handoff only; no application changes are implemented here. Implement the visual feature in a later coding task.

## Location and appearance

- Inspect the latest `frontend/about.html`: the public homepage currently has `#hero-title` inside `.cl-hero`, with the text `Find Your Way <span>Home.</span>`.
- Inspect the existing birds in the homepage hero artwork and the tools-page scenery in `frontend/index.html`. Reuse their recognizable SVG/CSS visual language, body shape, and attached-wing motion where practical. Use a small green variation; do not use an emoji, stock image, or a new icon style.
- Position the bird's feet on the upper-left portion of the capital **F**, so it visibly sits on the letter rather than floating beside the heading. Start around 20–28 CSS pixels wide on desktop and tune visually at the actual font size.
- Keep the title readable and preserve its wording, typography, colors, spacing, and responsive wrapping. Anchor the bird to the letter, not to a viewport coordinate or a guessed offset from the whole heading. Ensure any new wrappers do not accidentally inherit the existing special styling for the `Home.` span.
- The bird should start calmly perched, with folded wings. Avoid continuous distracting motion while it waits.

## Hover and flight behavior

1. Hovering over the **bird itself** triggers one takeoff. Hovering elsewhere on the headline should not launch it.
2. Animate a small upward lift, then a smooth flight upward and to the right with a few natural wing flaps. Suggested duration: about 800–1,200 ms, adjusted to fit the site.
3. Keep the wings attached to the body; avoid the disconnected/scissoring shapes called out in the earlier bird-animation handoff.
4. Let the bird leave the visible hero gracefully and fade out near the end. It must not be clipped immediately by the headline wrapper, create scrollbars, or shift the page layout.
5. Ignore additional hover events while the bird is departing. Once it has flown away, leave it gone for that page visit; a fresh page load may restore the perched bird. Do not instantly respawn it under the cursor.
6. Remove or disable its hit area after departure so no invisible element intercepts input. Existing background birds should continue behaving normally.

## Accessibility and implementation constraints

- Touch users should be able to tap the bird to trigger the same effect without interfering with scrolling or other controls.
- If implemented as an interactive control, use a real button with a concise accessible label such as “Let the bird fly away,” keyboard activation with Enter/Space, and a visible focus indicator. Do not turn the entire heading into a button or alter its accessible heading text.
- Respect `prefers-reduced-motion`: keep the perched bird still, and use an immediate dismissal or brief opacity fade instead of a moving flight path when activated.
- Keep the resting bird visible if JavaScript fails; the heading and all navigation must remain usable.
- Scope new styles and keyframes to this perched bird so they do not change existing flock animations. Use lightweight transforms and opacity, with no new animation library or network dependency.
- Preserve current header behavior, the Gemma introduction, and all other layouts and application logic.

## Acceptance checks

- Inspect the actual rendered bird at desktop, tablet, narrow mobile, and browser zoom: its feet stay anchored to the F, with no overlap obscuring the text, unwanted heading wraps, clipping, or horizontal scrolling.
- Verify the full takeoff and flight in a browser, not just a still frame. Check that leaving the original hover area does not interrupt or restart the flight.
- Test mouse hover, repeated hover, touch/tap, keyboard activation, and reduced-motion behavior.
- Confirm the bird stays gone after the flight, the former hit area no longer captures input, and a fresh page load restores the initial state.
- Check that the background birds, homepage links, and Get started/Gemma flow still work. Capture a perched preview and a representative flight frame if possible.

## Delivery

Inspect the latest `main`, implement the feature, and report what changed and which browser checks ran. Follow the user's workflow: `git add -A`, `git commit -m "Describe the change"`, `git pull --rebase origin main`, then `git push origin main`. Resolve conflicts while preserving teammates' changes and recheck affected behavior. Use `main`, not a new fix branch. Report the implementation commit hash; do not mark this handoff as implemented until the feature is built and checked.
