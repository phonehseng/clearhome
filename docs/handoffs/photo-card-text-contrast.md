# Handoff: subtle readability improvement on glass photo cards

> **Status: done, then superseded.** d180427 raised small-text contrast on the glass photo cards from about 2:1 to over 6:1 (measured against each card's photo); 8437f67 then replaced the glass cards with full photos above solid detail panels.

Implement, visually verify, commit, and push this user-requested refinement. The screenshot shows University Terrace — 1213K with dark text on a translucent, blurred property photo. The title and rent are readable, but the supporting text blends into the image. The user wants the font a little more visible while retaining the transparent photo/glass appearance.

- Inspect the latest photo-card styles and all relevant variants before editing. Improve supporting-text contrast modestly: use a slightly darker text color and, where helpful, a small font-weight increase. Preserve the clear title/rent hierarchy and avoid making every line bold.
- If text adjustments alone are insufficient across varied photos, modestly strengthen the local glass panel tint or use a subtle consistent scrim behind the text. Keep the property photo visible; this should be a restrained refinement rather than an opaque redesign or a return to excessive blur.
- Pay particular attention to address, rental type, room/shared-home description, availability caveats, fees/utilities, accessibility notes, and source actions. Keep important caveats as readable as the main details.
- Check actual computed contrast against the rendered backgrounds, including bright and dark photo regions. Aim for WCAG AA text contrast (4.5:1 for normal text and 3:1 for qualifying large text). Do not claim contrast compliance from a text color alone when its background is variable.
- Verify the University Terrace card and several visually different property photos on desktop and mobile, at browser zoom, plus no-photo cards. Avoid changing layout, prices, listing data, or photo sourcing as part of this small visual fix.
- Preserve save/share controls, focus visibility, and all interactions. Do not rely on heavy text shadows or outlines that make the font fuzzy.

Report the actual visual changes, browser/contrast checks, and implementation commit hash. Commit and push the UI changes; this handoff is only the request and does not itself fix the cards.
