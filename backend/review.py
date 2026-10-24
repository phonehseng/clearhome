"""Review records waiting in data/candidates.json before they reach users.

Usage:
    python backend/review.py list                      # counts per source, plus a sample
    python backend/review.py show <id>                 # full record
    python backend/review.py approve <id> [<id> ...]   # publish specific records
    python backend/review.py approve --source hud_pha  # publish every waiting record from one source
    python backend/review.py reject <id> [<id> ...]    # drop records and never re-import them

Approving marks a record verified with today's date and says it was imported from an
open-data API and approved by the team. Spot-check addresses and phones first.
"""
import argparse
import json
from collections import Counter
from datetime import date

from catalog import RESOURCES_PATH, validate_resources
from sources import CANDIDATES_PATH, _load_queue, _lock


def _save(queue, resources=None):
    CANDIDATES_PATH.write_text(json.dumps(queue, indent=2) + "\n")
    if resources is not None:
        RESOURCES_PATH.write_text(json.dumps(resources, indent=2, ensure_ascii=False) + "\n")


def cmd_list(queue, _args):
    waiting = queue["candidates"]
    print(f"{len(waiting)} waiting for review:")
    for origin, n in Counter(r["origin"] for r in waiting).most_common():
        print(f"  {origin}: {n}")
    for r in waiting[:15]:
        print(f"  - {r['id']}: {r['name']} | {r.get('jurisdiction')} | {r.get('phone') or 'no phone'}")


def cmd_show(queue, args):
    for r in queue["candidates"]:
        if r["id"] in args.ids:
            print(json.dumps(r, indent=2))


def cmd_approve(queue, args):
    today = date.today().isoformat()
    chosen = [r for r in queue["candidates"] if r["id"] in args.ids or r["origin"] == args.source]
    if not chosen:
        raise SystemExit("Nothing matched. Run `python backend/review.py list` to see ids and sources.")
    resources = json.loads(RESOURCES_PATH.read_text())
    for r in chosen:
        r["verified"] = True
        r["last_verified"] = today
        r["verification_method"] = r["verification_method"].replace(
            "not yet reviewed by the team.", f"approved by the team on {today}; no phone or in-person confirmation.")
    errors = validate_resources(resources + chosen)
    if errors:
        raise SystemExit("Not approved, fix these first:\n" + "\n".join(errors))
    ids = {r["id"] for r in chosen}
    queue["candidates"] = [r for r in queue["candidates"] if r["id"] not in ids]
    _save(queue, resources + chosen)
    print(f"Approved {len(chosen)} records; they are now live in {RESOURCES_PATH.name}.")


def cmd_reject(queue, args):
    ids = set(args.ids)
    before = len(queue["candidates"])
    queue["candidates"] = [r for r in queue["candidates"] if r["id"] not in ids]
    queue["rejected"] = sorted(set(queue["rejected"]) | ids)
    _save(queue)
    print(f"Rejected {before - len(queue['candidates'])} records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    for name in ("show", "reject"):
        sub.add_parser(name).add_argument("ids", nargs="+")
    approve = sub.add_parser("approve")
    approve.add_argument("ids", nargs="*")
    approve.add_argument("--source", help="approve every waiting record from this source")
    args = parser.parse_args()
    with _lock:
        queue = _load_queue()
        {"list": cmd_list, "show": cmd_show, "approve": cmd_approve, "reject": cmd_reject}[args.command](queue, args)
