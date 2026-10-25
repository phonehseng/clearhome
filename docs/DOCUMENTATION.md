# Clear House documentation

This documentation describes the implementation in this repository, not a promise that every external service or housing opportunity is available. Review the code and dated evidence when behavior or inventory changes.

## Start here

- **Using the website:** [User guide](USER_GUIDE.md).
- **Running it on your computer:** [Setup and troubleshooting](SETUP.md).
- **Changing the frontend or backend:** [Architecture](ARCHITECTURE.md), then [API reference](API.md).
- **Maintaining listings or releasing changes:** [Maintenance and testing](MAINTENANCE.md).
- **Deploying:** [Cloud Run deployment](../DEPLOY.md) and [optional GPU service](../gemma/README.md).

## Source-of-truth map

| Question | Source |
|---|---|
| Which pages and APIs exist? | `backend/app.py` and [API reference](API.md) |
| What housing evidence is stored? | `data/resources.json`, `data/VERIFICATION.md`, and `data/RESEARCH_LOG.md` |
| Which records are shown? | `backend/catalog.py`, review decisions, and runtime freshness filtering |
| Which images need review? | `data/photo_review.json`, `data/photo_sources.json`, and `data/photo_delivery_review.json` |
| How are deployments configured? | `Dockerfile`, `cloudbuild.yaml`, `.gcloudignore`, and [deployment guide](../DEPLOY.md) |
| What work has been handed off? | `docs/handoffs/` and root handoff notes; these are requests, not proof of completion |
| What checks actually ran? | Test command output, browser checks, dated `docs/audits/` reports, and commit history |

## Documentation conventions

Describe implemented behavior separately from planned work. Do not treat AI-generated suggestions as reviewed housing facts. Use unknown values rather than guessing prices, vacancies, dates, accessibility, route times, or photo identity. Keep credentials out of examples. When publishing counts, distinguish raw catalog records, filtered options, physical communities, and available image files.

The current pages are `/`, `/app`, `/resources`, `/google-cloud`, and `/review`. The old `/lease` page and document-upload APIs are absent. The current styling is light; automatic device dark mode is not active. See [known limitations](ARCHITECTURE.md#known-limitations).
