"""Answer "a place near X" questions: an office, a school, a hospital, a street address.

No AI is involved. A keyword script pulls the place out of the question; the US Census Geocoder (street
addresses) or Google Places Text Search (named places) finds it; reviewed listings are ranked by distance;
and Google Routes adds real commute times by car and by transit for the closest few.

Usage: python backend/nearby.py "I need a place near my office at 1800 Tysons Blvd"
"""
import json
import math
import os
import re
import sys
import threading
import time
import urllib.request

from advisor import LANDMARKS, OUTSIDE, URGENT, area_for
from catalog import filter_catalog, load_catalog
from geocode import lookup as census_lookup

PLACES_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
# Service regions: (name, latitude, longitude, radius in miles). Places outside them are politely refused.
REGIONS = [("Northern Virginia", 38.83, -77.30, 35), ("Blacksburg", 37.23, -80.42, 15)]
MAX_HOMES = 5
MAX_MILES = 15

# "by" and "around" are left out on purpose: "kicked out by my landlord", "around $1200".
NEAR = re.compile(r"\b(?:near|close to|closest to|next to|walking distance (?:to|of|from)|walk to|commute to|"
                  r"within \d+ (?:mi|miles?|minutes?|mins?) (?:of|from)|minutes? from|not far from)\s+(.+?)(?:[?!]|\.(?:\s|$)|$)", re.I)
WORKPLACE = re.compile(r"^(?:my|our|the)\s+(?:office|work|job|workplace|school|campus|hospital|kids'? school|daycare)\b"
                       r"(?:\s+(?:at|in|on|which is at|is at|located at)\s+)?", re.I)
STREET = re.compile(r"^\d+\s+[\w.' -]*\b(?:st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|ln|lane|ct|court|pike|hwy|highway|way|pl|place|pkwy|parkway|cir|circle|ter|terrace|sq|square|plaza)\b", re.I)
NOT_A_PLACE = re.compile(r"^(?:\$|\d+\s*(?:%|dollars|people|months?|weeks?|days?|years?|a month|per)|being|getting|losing|done|finished|term|the end|the (?:deadline|limit|max)|"
                         r"(?:next|this|last) (?:week|month|year)|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|christmas|thanksgiving|today|tomorrow|tonight|the weekend|midnight|noon)", re.I)
FILLER_END = re.compile(r"\s+(?:please|thanks|thank you|under \$?\d[\d,]*.*|for (?:me|my family|\d+ people).*|with .*)$", re.I)
_cache, _lock = {}, threading.Lock()


def _key():
    return os.environ.get("GOOGLE_MAPS_SERVER_API_KEY", "").strip()


def extract_place(question):
    """('1800 Tysons Blvd', None) for a findable place; (None, 'office') when they only said 'my office'; (None, None) otherwise."""
    m = NEAR.search(question or "")
    if not m or URGENT.search(question):
        return None, None
    place = FILLER_END.sub("", m.group(1).strip().rstrip(",;"))
    if NOT_A_PLACE.match(place):
        return None, None
    work = WORKPLACE.match(place)
    if work:
        rest = place[work.end():].strip()
        if not rest or rest.lower() == place.lower():
            kind = re.search(r"office|work|job|workplace|school|campus|hospital|daycare", place, re.I)
            return None, kind.group(0).lower() if kind else "place"
        place = rest
    # A real place is a street address, a landmark we know, or a name (a capitalized word like "Inova").
    known = any(re.search(rf"\b{re.escape(k)}\b", place.lower()) for k in LANDMARKS) or area_for(place) not in (None, "Northern Virginia")
    if len(place) < 3 or not (STREET.match(place) or known or re.search(r"\b[A-Z][A-Za-z]", place)):
        return None, None
    return place, None


def _miles(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def _post(url, body, mask):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": _key(), "X-Goog-FieldMask": mask})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.load(resp)


def locate(place):
    """(name, latitude, longitude) for a place inside a service region, or None."""
    key = place.lower()
    if re.search(OUTSIDE, key):
        return ("outside", None, None)
    with _lock:
        if key in _cache:
            return _cache[key]
    found = None
    landmark = next((v for k, v in LANDMARKS.items() if re.search(rf"\b{re.escape(k)}\b", key)), None)
    if landmark:
        found = (place.title(), landmark[1], landmark[2])
    elif STREET.match(place):
        region = "Blacksburg, VA" if area_for(place) == "Blacksburg" else "VA"
        try:
            point = census_lookup(place if re.search(r",\s*\w", place) else f"{place}, {region}")
        except Exception:
            point = None
        if point:
            found = (place, point[0], point[1])
    if not found and _key():
        # Named places (an employer, a hospital, a school): Google Places, biased toward Northern Virginia.
        bias = REGIONS[1] if area_for(place) == "Blacksburg" else REGIONS[0]
        try:
            data = _post(PLACES_TEXT_URL, {"textQuery": place, "maxResultCount": 1,
                                           "locationBias": {"circle": {"center": {"latitude": bias[1], "longitude": bias[2]}, "radius": 50000.0}}},
                         "places.displayName,places.formattedAddress,places.location")
            p = (data.get("places") or [None])[0]
            if p:
                found = (f"{p['displayName']['text']} ({p.get('formattedAddress', '')})", p["location"]["latitude"], p["location"]["longitude"])
        except Exception:
            found = None
    if found and not any(_miles(found[1], found[2], lat, lon) <= r for _, lat, lon, r in REGIONS):
        found = ("outside", found[1], found[2])
    with _lock:
        if len(_cache) > 500:  # keyed on user text, so keep it bounded
            _cache.clear()
        _cache[key] = found
    return found


def _commutes(homes, lat, lon):
    """Minutes by car and by transit from each home to the place (Google Routes), or {} if unavailable."""
    if not _key() or not homes:
        return {}
    out = {}
    for mode in ("DRIVE", "TRANSIT"):
        try:
            rows = _post(MATRIX_URL, {"origins": [{"waypoint": {"location": {"latLng": {"latitude": h["lat"], "longitude": h["lon"]}}}} for h in homes],
                                      "destinations": [{"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lon}}}}],
                                      "travelMode": mode}, "originIndex,duration,condition")
        except Exception:
            continue
        for row in rows if isinstance(rows, list) else []:
            if row.get("condition") == "ROUTE_EXISTS" and row.get("duration"):
                out.setdefault(row["originIndex"], {})[mode] = round(int(str(row["duration"]).rstrip("s")) / 60)
    return out


def answer(question, profile=None):
    """Text answer for a "near X" question, or None if the question isn't one."""
    place, vague = extract_place(question)
    if vague:
        return (f"Happy to look near your {vague}. What's the address or the name of the place? For example: "
                f"\"near my {vague} at 1800 Tysons Blvd\" or \"near Inova Fairfax Hospital\".")
    if not place:
        return None
    found = locate(place)
    if not found:
        return None
    name, lat, lon = found
    if name == "outside":
        return ("That place looks outside the areas Clear House covers (Northern Virginia and Blacksburg). "
                "For other areas, call 211 for local housing help.")
    profile = profile or {}
    filters = {"types": ["affordable_listing", "rental_listing"], "age": 62 if profile.get("senior") else 30}
    if isinstance(profile.get("budget"), (int, float)) and profile["budget"] > 0:
        filters["max_budget_per_month"] = profile["budget"]
    seen, homes = set(), []
    for r in filter_catalog(load_catalog(), filters):
        if r.get("lat") is None:
            continue
        key = (r.get("community") or r["name"]).casefold()
        if key in seen:
            continue
        seen.add(key)
        d = _miles(lat, lon, r["lat"], r["lon"])
        if d <= MAX_MILES:
            homes.append((d, r))
    homes = [r for _, r in sorted(homes, key=lambda x: x[0])[:MAX_HOMES]]
    if not homes:
        return (f"I don't have a reviewed home within {MAX_MILES} miles of {name} that fits your choices. "
                "Try a higher budget, or call 211 for local housing help.\n\nThis is guidance, not legal advice.")
    commute = _commutes(homes, lat, lon)
    lines = [f"Closest reviewed homes to {name}:"]
    for i, r in enumerate(homes):
        rent = f"from ${r['monthly_rent']:,.0f}/month" if isinstance(r.get("monthly_rent"), (int, float)) else "rent: ask the provider"
        miles = _miles(lat, lon, r["lat"], r["lon"])
        trip = ["at or next to this address" if miles < 0.1 else f"{miles:.1f} mi away"]
        if commute.get(i, {}).get("DRIVE"):
            trip.append(f"about {commute[i]['DRIVE']} min by car")
        if commute.get(i, {}).get("TRANSIT") and miles >= 0.1:
            trip.append(f"{commute[i]['TRANSIT']} min by transit")
        kind = " (regular rental, not income-restricted)" if r.get("type") == "rental_listing" else ""
        phone = f" Call {r['phone']}." if r.get("phone") else ""
        lines.append(f"- **{r.get('community') or r['name']}**{kind}: {rent}; {', '.join(trip)}.{phone}")
    lines.append(("Commute times are from Google and change with traffic and schedules. " if commute else "Distances are straight-line. ")
                 + "Advertised rents and openings aren't guaranteed, so confirm with the property.\n\nThis is guidance, not legal advice.")
    return "\n".join(lines)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    t = time.time()
    print(answer(" ".join(sys.argv[1:])) or "(not a near-place question)")
    print(f"\n[{time.time() - t:.1f}s]")
