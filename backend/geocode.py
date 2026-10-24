"""Add map coordinates to catalog records using the free US Census Geocoder (no key needed).

Run: python backend/geocode.py    # only looks up records that don't have coordinates yet
Records whose address the Census can't match (for example, no street number) are left without a pin.
"""
import json
import re
import time
import urllib.parse
import urllib.request

from catalog import RESOURCES_PATH
from sources import _lock

GEOCODER = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


def lookup(address):
    """Return (lat, lon) for a US street address, or None if the Census has no match."""
    # Drop suite/unit details and mailing notes that confuse the matcher.
    clean = re.split(r"\s*[;(]", address)[0]
    clean = re.sub(r",?\s*(Suite|Ste\.?|Unit|Apt\.?|#)\s*[\w-]+", "", clean, flags=re.I)
    query = urllib.parse.urlencode({"address": clean, "benchmark": "Public_AR_Current", "format": "json"})
    with urllib.request.urlopen(f"{GEOCODER}?{query}", timeout=30) as resp:
        matches = json.load(resp)["result"]["addressMatches"]
    if not matches:
        return None
    point = matches[0]["coordinates"]
    return round(point["y"], 6), round(point["x"], 6)


def geocode_catalog():
    with _lock:
        rows = json.loads(RESOURCES_PATH.read_text())
    found = missed = 0
    for row in rows:
        address = row.get("address")
        if row.get("lat") is not None or not address or not re.match(r"\s*\d", address):
            continue  # already placed, or no street number to match
        try:
            point = lookup(address)
        except Exception:
            point = None
        if point:
            row["lat"], row["lon"] = point
            row["geocode_source"] = "US Census Geocoder"
            found += 1
        else:
            missed += 1
        time.sleep(0.3)  # be polite to the free service
    with _lock:
        latest = json.loads(RESOURCES_PATH.read_text())
        placed = {r["id"]: r for r in rows if r.get("lat") is not None}
        for r in latest:
            if r.get("id") in placed and r.get("lat") is None:
                r["lat"], r["lon"], r["geocode_source"] = placed[r["id"]]["lat"], placed[r["id"]]["lon"], "US Census Geocoder"
        RESOURCES_PATH.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n")
    return found, missed


if __name__ == "__main__":
    found, missed = geocode_catalog()
    print(f"Placed {found} records on the map; {missed} addresses had no Census match.")
