# Handoff: shelter-specific links and actionable navigation

Investigate and implement the user's reported shelter-link problem. Cards for Katherine K. Hanley Family Shelter, Fair Ridge Shelter, FACETS Next Steps Family Program, and Bailey's Shelter and Supportive Housing show a generic **Website** action. Users land on an organization homepage or directory without knowing where to find their specific program or how to obtain help.

## Findings from repository and web inspection

- `data/resources.json` sets Hanley and Fair Ridge's `website` to https://www.shelterhouse.org/ and Next Steps and Bailey's to https://www.fairfaxcounty.gov/homeless/emergency-shelters . These destinations contain relevant information, but are broad destinations rather than individual intake pages.
- `frontend/index.html` uses `safeUrl(r.website) || safeUrl(r.source_url)` and labels the result **Website**. Also inspect `frontend/resources.html`, which renders the same generic action. Trace all API and Gemma consumers.
- The resource records already contain `how_to_apply`, `requirements`, `sources`, and notes that are not evident in the screenshot's short cards. Useful intake information should be surfaced instead of making users navigate away to discover it.
- Checked official references: https://www.shelterhouse.org/ , https://www.shelterhouse.org/shelters , https://www.fairfaxcounty.gov/homeless/emergency-shelters . Shelter House's homepage names Hanley and Fair Ridge, so do not characterize these as unrelated organizations. Recheck content and actual navigation before selecting a replacement URL; a shelters index alone may still be too general.
- The county directory has named expandable sections for the four programs. Next Steps uses distributed accommodation; its listed address is an office, not a single shelter entrance. Avoid sending people there as if it were overnight walk-in accommodation.
- A more relevant FACETS service page surfaced in research: https://facetscares.org/our-services/emergency-response-and-basic-needs/homelessness-housing-shelter/ . Open and inspect it before adopting it; do not assume it is a direct intake page.
- Search also surfaces an older operator's Bailey's page at New Hope Housing, while the current county directory identifies FACETS. Verify operator currency instead of choosing a specific-looking but outdated page. There are existing source-conflict notes in the records; resolve or expose relevant uncertainty.

## Required changes

1. Audit every shelter resource's destination against the exact program name, location, population served, and current operator. Prefer an official program-specific page that actually explains access. Validate redirects and the final content, not just HTTP success. Do not guess URL paths or fragments.
2. Separate link meanings in the data/rendering as needed: **Program details**, **Official county listing**, **Provider website**, and **How to get shelter** should accurately describe their destination. Do not label a county directory as a provider website or imply that a homepage is an intake portal.
3. When only a directory or homepage exists, retain it as a clearly labeled supporting source and provide a useful in-app detail view or expanded section for that program. Show who the service helps, verified access steps, referral requirements, intake hours when published, after-hours options, and a prominent call action. Clearly distinguish a direct shelter phone from a coordinated-entry/referral phone.
4. For directory links, use a tested stable anchor only if one exists and opens the correct section. If no dependable deep link exists, give explicit navigation guidance such as **Open [exact named section] under [category]**, while making essential instructions available within our app. Do not fabricate anchors or pretend the section opens automatically.
5. Verify public intake addresses before offering directions. Label office addresses as offices, do not infer walk-in admission, and protect confidential locations. Never equate program capacity with beds available tonight; retain call-to-confirm language unless current capacity is independently supported.
6. Apply the corrected records, labels, and access information consistently to resource cards, search results, and Gemma where applicable. Preserve safe URL handling and safe rendering. Audit similar generic links elsewhere in emergency-service listings.

## Validation and reporting

- In a browser, click the four screenshot examples and confirm each destination is relevant and every label is truthful. If an external page remains general, verify that the in-app view explains exactly how to proceed and where to find the named program externally.
- Check mobile and keyboard navigation, calls, directions, expandable details, and missing program-specific URL cases.
- Reverify intake facts against current official sources; timestamp actual reviews and preserve field provenance. Do not claim phone verification without making an authorized call.
- Run relevant project checks and focused coverage for link fallback/label behavior. Report corrected links per program, remaining general-only destinations, source conflicts, and validation.

This is a researched handoff, not an implemented fix or verification of current bed availability. Review the latest repository before editing because another agent may be changing these components.
