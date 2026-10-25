"""Third check that every listed place exists, from two independent sources (October 25, 2026):

1. Google Places: is there a place with a matching name at (or within half a mile of) our address, and is it operating
   or permanently closed? Confidential shelter locations are never looked up.
2. The place's own pages (source and website): do they load and name it? Pages that block automated visitors are
   recorded as blocked, never worked around.

A community counts as confirmed when Google lists it operating, or its own page names it. Permanently closed and
unconfirmed communities are listed for a person to check; nothing is changed here.

Run: python backend/existence_audit.py [--out report.json]   (needs GOOGLE_MAPS_SERVER_API_KEY in .env)
"""
import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.insert(0, os.path.dirname(__file__))
import nearby  # noqa: E402
from catalog import load_catalog  # noqa: E402
from source_audit import UA, _name_tokens, _text  # noqa: E402

MASK = "places.displayName,places.formattedAddress,places.location,places.businessStatus,places.types"


def _tokens(name):
    return set(_name_tokens(name or ""))


def _number(address):
    m = re.match(r"\s*(\d{2,6})\b", address or "")
    return m.group(1) if m else None


def places_check(row):
    """{"status": OPERATIONAL/CLOSED_PERMANENTLY/..., "match": name, "address": ..., "miles": ...} or {"status": "not_found"}."""
    name, address = row.get("community") or row["name"], row.get("address") or ""
    if row.get("confidential_location"):
        return {"status": "skipped_confidential"}
    query = f"{name}, {address}" if address else f"{name}, {row.get('city') or row.get('jurisdiction') or ''}, VA"
    try:
        data = nearby._post(nearby.PLACES_TEXT_URL, {"textQuery": query, "maxResultCount": 5}, MASK)
    except Exception as error:  # noqa: BLE001
        return {"status": "error", "error": str(error)[:120]}
    want, number = _tokens(name), _number(address)
    best = None
    for p in data.get("places") or []:
        got = _tokens((p.get("displayName") or {}).get("text", ""))
        overlap = len(want & got) / max(1, len(want))
        loc = p.get("location") or {}
        miles = (nearby._miles(row["lat"], row["lon"], loc["latitude"], loc["longitude"])
                 if isinstance(row.get("lat"), (int, float)) and loc else None)
        here = (miles is not None and miles <= 0.5) or (number and number in (p.get("formattedAddress") or ""))
        score = overlap + (1 if here else 0)
        if (overlap >= 0.5 or (here and overlap > 0)) and (best is None or score > best[0]):
            best = (score, p, miles, here, overlap)
    if not best:
        return {"status": "not_found"}
    _, p, miles, here, overlap = best
    return {"status": p.get("businessStatus") or "UNKNOWN", "match": (p.get("displayName") or {}).get("text"),
            "address": p.get("formattedAddress"), "miles": None if miles is None else round(miles, 2), "at_address": bool(here),
            "name_overlap": round(overlap, 2)}


def page_check(url, name):
    """'names_it' (loads and names the place), 'loads' (loads, doesn't name it), 'blocked' (403/429/401), or an HTTP status."""
    if not url or not str(url).startswith("http"):
        return None
    try:
        r = requests.get(url, headers=UA, timeout=15)
    except requests.RequestException as error:
        return f"error: {type(error).__name__}"
    if r.status_code in (401, 403, 429):
        return "blocked"
    if r.status_code != 200:
        return f"http {r.status_code}"
    if "html" not in r.headers.get("Content-Type", ""):
        return "loads (not a web page)"
    text = _text(r.text)
    tokens = _tokens(name)
    return "names_it" if tokens and sum(t in text for t in tokens) >= max(1, round(0.7 * len(tokens))) else "loads"


def audit():
    rows = load_catalog()
    communities = {}
    for r in rows:  # one check per community (floor plans share a building)
        communities.setdefault((r.get("community") or r["name"]).casefold(), r)
    reps = list(communities.values())
    with ThreadPoolExecutor(4) as pool:
        places = list(pool.map(places_check, reps))
    with ThreadPoolExecutor(8) as pool:
        sources = list(pool.map(lambda r: page_check(r.get("source_url"), r.get("community") or r["name"]), reps))
        websites = list(pool.map(lambda r: page_check(r.get("website"), r.get("community") or r["name"])
                                 if r.get("website") and r.get("website") != r.get("source_url") else None, reps))
    report = []
    for r, pl, src, web in zip(reps, places, sources, websites):
        page_ok = "names_it" in (src, web)
        if pl.get("status") == "CLOSED_PERMANENTLY":
            verdict = "closed_per_google"
        elif pl.get("status") == "OPERATIONAL" or page_ok:
            verdict = "confirmed"
        elif pl.get("status") in ("CLOSED_TEMPORARILY",):
            verdict = "temporarily_closed"
        else:
            verdict = "unconfirmed"
        report.append({"id": r["id"], "name": r.get("community") or r["name"], "type": r.get("type"), "jurisdiction": r.get("jurisdiction"),
                       "address": r.get("address"), "verdict": verdict, "places": pl, "source_page": src, "website": web,
                       "records": sum((x.get("community") or x["name"]).casefold() == (r.get("community") or r["name"]).casefold() for x in rows)})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="existence_report.json")
    args = parser.parse_args()
    if not nearby._key():
        sys.exit("GOOGLE_MAPS_SERVER_API_KEY is not set.")
    report = audit()
    json.dump(report, open(args.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    counts = {}
    for item in report:
        counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1
    print(len(report), "communities:", counts)
    for item in report:
        if item["verdict"] != "confirmed":
            print(f"{item['verdict']:>20} | {item['name'][:60]} | {item['type']} | places={item['places'].get('status')} "
                  f"{item['places'].get('match') or ''} | source={item['source_page']} | site={item['website']}")


if __name__ == "__main__":
    main()
