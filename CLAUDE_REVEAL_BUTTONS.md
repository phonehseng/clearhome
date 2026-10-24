# Claude handoff: housing listing reveal buttons

Please implement and verify the user's latest request for listing reveal controls. This request supersedes earlier batch-size preferences in chat or handoff files.

The user reports that revealing only nine additional listings feels too slow. They want a normal reveal button that adds a useful batch (12, 15, or 18), plus a separate reveal-all button.

- Use **18 additional communities per click** for the default **Show more communities** button (or all remaining communities if fewer than 18 remain).
- Keep a separate **Show all** button that reveals every remaining community matching the current filters.
- Make Show more the larger primary button and Show all a smaller secondary control. Do not put batch sizes in the button labels.
- **Latest label requirement:** Remove the parenthetical count such as **(191 more)** from **Show all communities**. Its entire label should be **Show all communities**. Keep the dynamic remaining count on the other button, for example **Show more communities (191 remaining)**. Never hardcode 191; derive it from the remaining filtered results. This supersedes the earlier request for no numbers on either button. Commit `d20360e` already implements these labels locally/in the repository; preserve them and check that the deployed version uses them when doing the rest of this work.
- Hide the controls when every matching community is visible. Keep result counts accurate and preserve filters, sorting, and expanded floor-plan details when revealing more.
- Keep keyboard focus useful when a clicked control disappears. Verify desktop and mobile layouts.

Inspect the current implementation in `frontend/index.html` before changing it. Previous work added both controls and used a batch of 20; the user's report may refer to a deployed version with different behavior. Check the actual click handlers and any responsive or deployed variant rather than assuming the current batch is nine. Report any deployment mismatch instead of claiming it was fixed by a code change alone.

Validate that Show more adds 18, Show all reveals all remaining matches, and the final partial batch works correctly. Report the change and validation. This handoff itself does not implement the change or confirm a deployment.

---

**Implemented (2026-10-24, e83d1d9).** Show more reveals 18 per click with "Show more communities (N remaining)"; "Show all communities" has no count and hides when 18 or fewer remain (Show more already reveals them). Kept your primary/secondary styling and added a hover lift, a staggered fade-in for new cards, and a smooth scroll to the first new card (both off under reduced motion). Checked in the browser: 6 → 24 (231 → 213 remaining); Blacksburg 9 remaining → 15, both controls hidden, focus on the first new card. Deployed in the same Cloud Run release.
