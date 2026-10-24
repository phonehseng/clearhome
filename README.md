# mlhhackathonbacteriagang

Group hackathon effort by Pierce, Umair, Phone, and Ryan for **GDG Build with AI x Hacktoberfest 2026** (Virginia Tech, Oct 24-25, 2026). Theme: **AI for Housing**.

## Problem

Finding safe, affordable housing is hard for low-income people, especially students and families in crisis. Listings are scattered, fake and scam listings are common, leases are full of confusing legal language, and emergency help is hard to find when you need it fast.

## Solution

An AI housing assistant, powered by Gemma 4, that helps people:

- **Find affordable housing.** Matches a person's budget, location and accessibility needs to manually verified affordable and low-income housing listings.
- **Find emergency help.** Points people to verified shelters and emergency housing resources, with urgent cases shown first.
- **Check a lease or listing.** Explains a lease in plain language, flags risky clauses, and warns about signs of a scam or fake listing.

To avoid made-up information, the assistant only recommends places from our hand-verified resource list (`data/resources.json`). The lease and scam checks are informational and are not legal advice.

## Tech used

_Models (e.g. Gemma 4), Google Cloud services, frameworks. (TODO)_

## Getting started

```bash
git clone https://github.com/phonehseng/mlhhackathonbacteriagang
cd mlhhackathonbacteriagang
```

_Setup and run instructions, API dependencies, environment variables (copy `.env.example` to `.env`). (TODO)_

## Responsible AI, privacy and accessibility

- **Safety and grounding:** _guardrails against hallucinations and harmful output (TODO)_
- **Privacy:** _what data we collect and why (TODO)_
- **Accessibility:** _keyboard navigation, contrast, screen-reader support (TODO)_

## Team workflow (see [CONTRIBUTING.md](CONTRIBUTING.md) for the full git guide)

- Pull before you start: `git pull`
- Work on a branch: `git checkout -b your-feature`
- Never commit secrets or API keys (`.env` is gitignored)

## License

[MIT](LICENSE)
