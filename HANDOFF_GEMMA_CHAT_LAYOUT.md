# Handoff: polish Ask Gemma chat and housing result cards

Please redesign and fix the Ask Gemma chatbot results presentation to the best of your ability within the existing site's design. The user says the current layout looks awkward and wants it to look polished. This is a UI improvement request, not a request to intentionally worsen the design.

## Problems visible in the user's screenshot

- Housing results occupy a large three-column grid inside a scrolling chat panel. Cards feel oversized for a conversation and leave excessive empty space.
- One listing without a photo displays concatenated text: **Coming soonMargotAlexandria City425 Montgomery St., Alexandria, VA 22314**. Status, name, locality, and address need distinct blocks and spacing.
- Photo cards have inconsistent presentation: text panels overlap photos and a strip of the image appears again below one card's content. A card without a photo stretches into a mostly empty white box beside them.
- Long addresses and action links wrap awkwardly. Card spacing, heights, image treatment, and visual hierarchy feel inconsistent.
- The large scrollable results region and composer need to feel like one coherent chat interface, with readable messages and a useful amount of results visible.

## Requested implementation

1. Inspect Gemma's actual message/result renderer and CSS. Reproduce results with photos, missing photos, missing fields, long names/addresses, and mixed availability statuses. Identify any shared listing styles leaking into chat cards or conditional markup that omits required wrappers.
2. Give chat results a consistent component structure: status badge, property title, locality, rent when known, address, and clearly separated actions. Render data safely and preserve working source, map, and phone links. Do not fabricate missing details or availability.
3. Use a clean, compact layout appropriate for a conversation. Choose responsive stacked cards or a restrained grid based on the available chat width. Avoid stretching cards to fill empty height. Keep images in a predictable aspect-ratio region with content below; eliminate background-image strips and unintended overlays. Missing-photo listings should retain the same readable information structure, using an understated fallback only where useful.
4. Improve typography, whitespace, contrast, borders, and alignment. Keep the design consistent with Clear House and give the property title and rent a clear hierarchy. Ensure status text never runs into the name or address.
5. Keep the composer easy to reach and fully usable while messages/results scroll. Avoid horizontal overflow, unnecessary nested scroll areas, or automatic scrolling that drags a user away from results they are reading. Preserve streaming responses and existing chat/search behavior.
6. Handle loading, empty results, errors, and partial streaming content gracefully. Any result expansion or pagination should have clear controls without overwhelming the conversation.
7. Verify keyboard access, focus visibility, descriptive links, mobile/touch layouts, light/dark appearance where supported, and browser zoom. Respect reduced motion if adding animation.

## Acceptance criteria

- Margot or another no-photo listing has properly separated status, title, locality, address, and links.
- Photo and no-photo results look intentionally designed together, without giant empty cards, duplicated image strips, or overlapping text.
- Results fit the chat panel on mobile and desktop, including long addresses and multiple results. The composer remains usable.
- Streaming, message history, source/map links, and phone actions continue to work.
- Inspect rendered UI in the browser at representative widths and with mixed result data. Run relevant existing checks and report what changed, what was verified, and any limitations.

This file is a handoff only; it does not implement the redesign or establish that the screenshot's defects have been reproduced locally.
