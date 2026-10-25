# Handoff: finish the listing sweep (2026-10-25)

All work from the listing sweep is on branch `main-f0h2dp`, in draft PR #2 (base `main`). The branch includes this file. Every `backend/test_*.py` passes except `test_gemma.py`, which needs the GPU. `python backend/catalog.py --check` passes: 433 records, 270 housing communities.

## Ground rules (from the project owner)

- No AI co-author lines in commits, and no AI-tool mentions in commits or repo files.
- Never commit `.env`, API keys (`AIza`, `AQ.`) or `.venv`. Never force-push. Pull with rebase.
- When merging teammates' work, keep both sides and never revert their features.
- Data comes from official sources only. Don't scrape sites that block bots, and never claim a shelter bed is free.

## Steps

1. **Merge PR #2.** `main` has no new commits since the branch was made, so it merges cleanly (fast-forward).
   ```bash
   git checkout main && git pull --rebase && git merge --ff-only origin/main-f0h2dp && git push
   ```
   Or mark #2 ready on GitHub and merge it there.
2. **Delete the old side branch.** It holds the same commits under an AI author name. PR #1 is already closed.
   ```bash
   git push origin --delete <the old dark-mode branch>
   ```
   You can also delete `main-f0h2dp` after the merge.
3. **Redeploy to Cloud Run** from a machine that has gcloud and the local `.env` (see `DEPLOY.md`). The live site, https://clear-house-875094537886.us-east4.run.app, is still running `ea5ec94`.
4. **Turn the GPU back down after Sunday evening (Oct 25, 8pm).** The local cron that was going to do this has stopped. Set the `gemma4` service back to min-instances 0.
5. **Work the human-check list.** Open `/review` on the running site. Each flagged item is listed in `docs/audits/2026-10-24-listing-sweep.md` with what to call or check. Most need a phone call:
   - Broadfalls: 540 number
   - Arbelo: two numbers that disagree
   - Poland Hill: rent
   - 1203 N Main: move-in date
   - Raines homes: whether they're still vacant
   - NRCA: phone number
   - Fieldstone and Highlands: phone numbers
   - 63 property websites that couldn't be confirmed automatically
6. **Map pins.** About 25 housing records still have no coordinates, mostly new construction. Geocode them from the official address and check each point against `data/nova_boundaries.geojson`.

## Already done (no action needed)

These were open items before the sweep. All are fixed on the branch:

- Chat cards skip generic place names.
- "Cheapest near X" sorts by rent.
- `/api/listings` is about 85 KB instead of 3 MB.
- The chat says when Gemma is warming up and shows plain progress steps instead of the model's raw notes.
- The map dropdown only lists areas with at least two communities.
- `/review` page.
- Phone links dial the right number.
- Fieldstone family and senior buildings show as separate cards.
