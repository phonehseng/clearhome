# Handoff: housing listing reveal buttons

Please implement and verify the user's latest request for listing reveal controls. This request supersedes earlier batch-size preferences in chat or handoff files.

The user reports that revealing only nine additional listings feels too slow. They want a normal reveal button that adds a useful batch (12, 15, or 18), plus a separate reveal-all button.

- Use **18 additional communities per click** for the default **Show more communities** button (or all remaining communities if fewer than 18 remain).
- Keep a separate **Show all** button that reveals every remaining community matching the current filters.
- Make Show more the larger primary button and Show all a smaller secondary control. Keep the labels simple; do not put batch sizes in the button labels.
- Hide the controls when every matching community is visible. Keep result counts accurate and preserve filters, sorting, and expanded floor-plan details when revealing more.
- Keep keyboard focus useful when a clicked control disappears. Verify desktop and mobile layouts.

Inspect the current implementation in `frontend/index.html` before changing it. Previous work added both controls and used a batch of 20; the user's report may refer to a deployed version with different behavior. Check the actual click handlers and any responsive or deployed variant rather than assuming the current batch is nine. Report any deployment mismatch instead of claiming it was fixed by a code change alone.

Validate that Show more adds 18, Show all reveals all remaining matches, and the final partial batch works correctly. Report the change and validation. This handoff itself does not implement the change or confirm a deployment.
