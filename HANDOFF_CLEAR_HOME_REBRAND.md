# Handoff: rebrand Clear House to Clear Home

The user has explicitly chosen the new product name **Clear Home**. Implement the rebrand throughout the product, visually verify it, commit, and push to main using the project's normal workflow. This handoff alone does not satisfy the implementation request.

## Brand and visual treatment

- Change the displayed logo wordmark from **clear house.** to **clear home.**, preserving intentional lowercase styling and the existing house icon unless a small alignment/spacing adjustment is needed. Use **Clear Home** for normal prose and titles.
- Update all visible product-name occurrences across the landing page, tools, resources, review, Google Cloud page, footer, navigation, dialogs, loading/error states, share text, chat greetings, generated responses, and any other user-facing views.
- Polish wordmark spacing, icon alignment, responsive sizing, and surrounding layout for the new name. Verify desktop/mobile, sticky headers, blue/light backgrounds, browser zoom, and image-based variants. Preserve the existing visual identity rather than introducing an unrelated redesign.
- Inspect generated assets and their source scripts. Update any logo image/SVG containing the old wordmark, plus accessible names, alt text, page titles, descriptions, social metadata, manifests, and structured data where present. Regenerate affected assets from their maintained sources rather than editing generated output alone.

## Comprehensive audit without breaking existing users

- Search case-insensitively for **Clear House**, **clear house**, **ClearHouse**, and relevant product references to **clearhouse**. Update active README/docs, application prompts/system messages, templates, and tests/fixtures that assert the product name. Distinguish real product references from unrelated housing terminology.
- Keep existing URLs, Cloud Run service names, repository remotes, deployment identifiers, API contracts, and credentials working. The user has authorized a product rebrand, not deletion/recreation of infrastructure or a repository rename. Do not invent a new public domain. Report old-name infrastructure references that intentionally remain.
- Inspect local-storage keys and internal JavaScript globals before renaming. Preserve saved favorites and other user state with compatibility or migration if changes are needed. Do not mass-replace technical identifiers blindly.
- Historical commit messages and archived handoffs can retain their original names where appropriate. Avoid churn in provenance/source data or third-party organization names. Make the current product consistently say Clear Home.
- Inspect the existing deployment process and deploy through it if authorized by repository/session instructions. Clearly distinguish pushed code from a verified live deployment.

## Validation and report

Run the project's relevant checks and search again for unintended old branding. Inspect the rendered logo and main pages at desktop and mobile widths, and exercise chat greetings, share actions, and favorites persistence. Verify links and assets load without regressions. Report the implementation commit, any intentional technical old-name references, checks performed, and deployment status.
