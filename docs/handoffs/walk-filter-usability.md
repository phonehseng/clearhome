# Handoff: make nearby-place and walking-time controls intuitive

Please implement, validate, commit, and push this user-requested usability improvement. Inspect the latest repository before editing.

## User feedback and current UI

In `frontend/index.html`, the optional housing-search fields **Live near a…** (`find-amenity`) and **Within a walk of** (`find-walk`) sit across from each other in an `input-row`. The user found their relationship confusing when reading from the right. They want the boxes less horizontally long, but a little larger overall in readability and comfortable control size.

## Suggested design to implement

- Group these two controls into one clearly labeled optional section, such as **Nearby essentials**, with a short explanation: **Find homes within your chosen walking time of a nearby service.** Make it clear that the time is measured between the home and the selected amenity, not from the user's current location.
- Replace the incomplete labels with self-contained labels: **Place to be near** and **Maximum walking time**. Keep existing amenity choices and walking-time values unless a verified product reason requires a change.
- Give the group a clear reading order and visual relationship so neither field looks like an unrelated tab. An optional short summary, such as **Supermarket within a 10-minute walk**, can reinforce the selected relationship without adding clutter.
- When **No preference** is selected, disable or hide the walking-time field with an accessible explanation that choosing a nearby service enables it. Do not apply a walking constraint when no amenity is selected. Verify existing behavior before changing request logic.
- Make the fields shorter in width with a sensible max-width or compact grid rather than stretching them across all available space. Increase readable text size and comfortable vertical padding modestly; retain at least 44px touch targets. Do not simply shrink the entire controls or create a sprawling full-width panel.
- On narrow screens, stack the fields in a logical order with clear spacing. Avoid clipped labels, horizontal scrolling, or excessive blank space on desktop. Follow the existing Clear House design.
- Keep labels programmatically associated, keyboard operation and focus clear, and any helper text connected to its control. Do not let a disabled field submit an unintended constraint through custom JavaScript.

## Validation

Test No preference, each amenity, changing walking time, clearing the amenity after a selection, and submitting the housing search. Preserve the existing walking-search API behavior and verify that the chosen maximum walking time is honored. Check mobile and desktop, keyboard navigation, and browser zoom. Report the changes, checks, commit, and any deployment limitations.

This handoff requests implementation; it does not itself change the form.


---

**Implemented (2026-10-24).** The two fields are now one **Nearby essentials** group (a fieldset with a legend and connected helper text: "Find homes within your chosen walking time of a nearby service. The walk is measured from each home to that place, not from where you are now."). Labels are **Place to be near** and **Maximum walking time**; choices and values are unchanged. Fields sit in a compact two-column grid capped at 230px each (stacked on phones), with 15px text and 46px-tall controls. **Maximum walking time** and "The walk is nice to have, not a must" (moved into this group) are disabled until a place is chosen, and a live summary reads e.g. "Supermarket within a 10-minute walk of the home." Request logic is unchanged: no walking constraint is sent without a place.

Checked in the browser: No preference → walking time disabled; Supermarket → enabled, summary updates, 15 minutes updates it; clearing the place disables it again; Pharmacy + 5 minutes + submit sends `requiredAmenity: "pharmacy", maxWalkingMinutes: 5, strict: true` to `/api/housing/search`.
