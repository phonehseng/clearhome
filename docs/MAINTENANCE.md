# Maintenance, testing, and release checks

## Responsibilities and publication

The team maintains the catalog as files in Git. Discovery, a review label, a successful image request, and a confirmed vacancy are separate events. Never change a verification date merely to keep a record visible. Never invent a price, accessibility feature, lease arrangement, source image, or route measurement.

Raw catalog counts differ from what users see: loading removes invalid/unverified/hidden records and deduplicates options, filters remove unsuitable or stale options, and community grouping combines plans. Describe the population whenever reporting a count.

## Review an existing record

1. Pull the latest `main` and run the local application.
2. Open `/review`; inspect the record's sources, validation issues, dates, status, and current decision.
3. Check the exact provider/property identity and evidence. Call the provider when needed; record what was actually established.
4. Choose **verified**, **flagged**, **hidden**, or clear the decision. A flag records a concern; hidden records are excluded by catalog loading. The verified decision does not automatically replace evidence dates or make an unverified canonical record publishable.
5. Update canonical facts/evidence where genuinely rechecked. Inspect `data/listing_review.json` and any catalog diff before committing.
6. Validate and publish the data with the normal Git workflow. The hosted site changes only after a deployment includes the new files.

HTTP saves require a local loopback connection and `CLEARHOME_READ_ONLY` unset. The hosted page should remain read-only. This local restriction is not an account/role system.

## Add a listing

Use the interactive helper for a reviewed provider source:

```bash
python backend/add_listing.py --dry-run
```

It asks questions and can optionally geocode an address. Review the preview before running `python backend/add_listing.py` to save. Keep the correct type (`affordable_listing` versus `rental_listing`), geography, room/whole-home rent basis, term/payment schedule, shared-lease responsibility, source evidence, and availability dates. Use null for unknown numeric prices. Avoid duplicating an existing community/floor-plan option.

See [catalog maintenance](../data/README.md) and [verification evidence](../data/VERIFICATION.md) for field details. Some older notes describe removed lease functionality; the current route implementation and [architecture](ARCHITECTURE.md) describe what is available today.

## Candidate discovery and approval

These commands can access networks and write files; they are maintenance actions, not required startup steps.

```bash
python backend/sources.py
python backend/review.py list
python backend/review.py show <candidate-id>
```

After reviewing actual evidence, use `python backend/review.py approve <candidate-id>` or `python backend/review.py reject <candidate-id>`. Approval is a publication decision, not a substitute for checking the source. Confirm that required availability/rent details are adequate for the intended search; an approved community directory record is not automatically a vacant apartment.

Open-data refresh is normally interval-limited. `--force` bypasses the refresh interval. Live web discoveries are separately labeled unreviewed; writable local calls can queue them. `CLEARHOME_READ_ONLY=1` disables application-triggered queue/review/freshness writes, but standalone CLI scripts still need careful use.

## Sources and freshness

```bash
python backend/catalog.py --check
python backend/source_audit.py --dry-run
```

Catalog validation is offline. Source auditing inspects/normalizes source roles and provider links; without `--dry-run` it writes changes. Read the script's output and diff before accepting changes. A directory link is not necessarily the provider's application page.

`python backend/freshness.py` checks provider pages using external services and can update the catalog. It is not a harmless health check. Automated findings can close or mark a listing for recheck; they do not confirm a new vacancy or renew manual verification. Blocked automated access does not prove a property is closed. Review resulting changes before committing. Keep dates tied to actual evidence and make ambiguous cases explicit.

## Images and licensing

Image metadata belongs to the exact property/community. Reuse across floor plans only when they describe that same community. Do not replace missing property imagery with a logo, stock photo, neighboring building, or unlabeled rendering.

| File | Role |
|---|---|
| `data/photo_sources.json` | Supporting source pages and source-review decisions |
| `data/photo_review.json` | Missing/rejected/pending image work |
| `data/photo_delivery_review.json` | Dated connector-delivery observations, including unconfirmed and unchecked URLs |
| `.cache/listing-photos/` | Ignored downloaded image bytes, not catalog facts |

Official renderings need `kind: "rendering"` and a clear caption stating they are not current photos. Licensed archive exceptions need the photographer, date, source, license link and required attribution. Beasley Square is an explicitly approved archive-photo exception; this is not blanket approval to use arbitrary third-party photography.

```bash
python backend/photo_audit.py
python backend/photo_audit.py --download --require-complete
python backend/listing_photos.py
```

The first inspects cached images without downloading. The second downloads canonical images and reports record-level gaps, failed/unvalidated delivery, and native dimensions. `--require-complete` exits unsuccessfully when required images cannot be validated; small images are reported separately and can still count as delivered. The importer prefetches unique images and returns a failure status when some downloads fail. None generates replacement images or proves property identity/availability.

The current coverage audit operates on `load_catalog()` output, after its validation, hidden-record and deduplication rules. It does not count every raw JSON row. For a complete editorial inventory, inspect the raw file and review queue as well. A record with metadata, a connector returning an image, a validated local download, and a high-resolution original are distinct coverage measures.

If a source requires a new image hostname, review it before adding an exact HTTPS host to `listing_photos.ALLOWED_HOSTS`. Do not broaden the route into an arbitrary-URL proxy. Preserve byte/pixel limits, image validation, attribution and failure states.

## Offline verification

Activate the virtual environment and run from the repository root:

```bash
python backend/catalog.py --check
python -m unittest discover -s backend -p 'test_[abchlnrw]*.py' -v
```

The current filename pattern selects offline suites for catalog/matching, expansion, categories, Blacksburg, chat behavior/streaming, nearby/walking, image handling, review and adding listings. `test_gemma.py` is a live API smoke script and is intentionally excluded. Emergency-service tests can be run separately:

```bash
python -m unittest discover -s backend -p 'test_emergency_services.py' -v
```

Do not run broad `test_*.py` discovery assuming every file is offline. If a new suite's name falls outside these patterns, run it explicitly or update the documented command. Mocked external responses verify application behavior, not current service availability, housing facts or route accuracy.

An optional AI check is `python backend/test_gemma.py`; it needs working credentials and makes real calls. Live Maps, provider-download and GPU checks are separate integration exercises and may consume service quota.

## Browser checklist

Serve the app through Flask and check current pages `/`, `/app`, `/resources`, `/google-cloud`, and `/review`.

- Check desktop and narrow/mobile widths, zoom, keyboard navigation, focus visibility and reduced-motion settings.
- Try default and empty searches, location/budget/category/age/room filters, and grouped floor-plan details. Confirm a per-person installment is not relabeled as whole-home monthly rent.
- Save, unsave, reload and share a listing. Confirm the shared URL opens the intended record and storage failure does not break the page.
- Check photo hover/enlargement, Enter/Escape, focus return, correct source/credit/license, rendering labels, server-download failure, direct-source fallback and total delivery failure.
- Confirm useful text remains selectable while controls/decorations resist accidental selection.
- Test chat's instant, streaming, AI-unavailable, interrupted and empty-input states. Check resource cards and official links.
- Check the strict/preferred walking distinction, unknown coordinates, unavailable routes, missing credentials and map/list behavior.
- Confirm emergency support stays in the requested service region and source links open the intended provider/service.
- Verify hosted review writes are rejected. Do not test production mutations to verify the local editor.

The current site is light-only despite earlier dark-mode work. A device-setting layout check is not proof of a dark visual theme. Also inspect text against actual bright/dark photo regions: passing a contrast check on a text color alone does not establish readable photo-card contrast.

## Deployment and operations

[DEPLOY.md](../DEPLOY.md) documents the project's Cloud Run service, secrets and trigger setup. `cloudbuild.yaml` describes photo prefetch, container build/push, and Cloud Run deployment. The Dockerfile uses Python 3.12, Gunicorn, read-only mode and example warm-up.

A push may trigger deployment **if the Cloud Build trigger is connected and enabled**. The YAML file is not proof that a trigger ran or a release is healthy. Check Cloud Build execution and Cloud Run revision status before reporting a live release. This documentation task does not itself validate cloud access, billing or deployed service health.

For a manual container build, `.cache/listing-photos/` must exist because the Dockerfile copies it. Run the importer on an allowed network and create the cache directory if necessary; a provider block can leave images absent. The Cloud Build photo step tolerates download failures and creates the directory, so a successful build does not establish complete photo coverage.

After a release, check page responses, catalog responses and counts, representative real image downloads, optional chat/Maps services, streaming behavior, source links, and read-only review status. Check logs for errors without copying secrets or user questions into public issue reports. Cache, provider and model outages need separate diagnosis.

To revert a bad shared code release, coordinate with the team and use an ordinary revert commit rather than force-pushing shared history. Reverting code/data in Git and redeploying it are separate steps. Avoid changing credentials or deleting cloud resources as part of routine documentation or UI work.

## Git workflow and attribution

For this project, work directly on **main** as requested by the project owner. Check the branch and pull before editing. Coordinate shared files; the root `README.md` is currently maintained by phonehseng.

```bash
git status -sb
git pull
# Edit and verify the intended files.
git add -A
git commit -m "Describe what changed"
git pull
git push
```

Inspect `git diff` and `git diff --cached` before committing; `git add -A` stages all changes in the working tree, including unrelated edits and deletions. Never commit `.env`, credentials, local environments or downloaded image caches. Resolve ordinary merges without discarding teammates' work; do not force-push to bypass a conflict.

This workspace credits **BUmair** using a repository-local identity:

```bash
git config --local user.name BUmair
git config --local user.email 165915147+BUmair@users.noreply.github.com
git log -1 --format=fuller
```

Other contributors should use their own verified GitHub identity. Author/committer settings apply to new commits; changing them does not rewrite existing history. A `.mailmap` can change displayed names locally without changing the original commit object.

## Keep documentation current

Update the relevant guide when routes, environment variables, schema, UI behavior, storage, limitations or deployment steps change. Keep root README edits coordinated with its owner. Documentation belongs in `docs/`; [DOCUMENTATION.md](DOCUMENTATION.md) is the entry point. Dated audit and handoff files preserve their original scope; a request in a handoff is not a completed implementation.
