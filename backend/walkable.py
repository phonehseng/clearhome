"""Find reviewed affordable housing within walking distance of a supermarket (or pharmacy / transit stop).

The request is read by a keyword script (no AI call). The catalog decides which homes are real and
affordable; Google Places (New) finds nearby stores; Google Routes measures the actual walking time.
Nothing here is invented: missing coordinates, failed routes and missing photos are reported as such.

Needs GOOGLE_MAPS_SERVER_API_KEY in .env (Places API + Routes API). See WALKABILITY.md.
Usage: python backend/walkable.py "under $1500 with a supermarket within a 10 minute walk in Arlington"
"""
import json
import math
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from advisor import area_for
from catalog import filter_catalog, load_catalog

PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"
MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Cost controls: a bounded number of homes and stores per search, and short-lived in-memory caching.
MAX_HOMES = 6
MAX_PLACES = 3
CACHE_SECONDS = 6 * 3600
WALK_METERS_PER_MINUTE = 84  # about 5 km/h; only sizes the search circle, never used as the walking time

AMENITIES = {
    "supermarket": {"label": "Supermarket", "types": ["supermarket", "grocery_store"],
                    "words": ("supermarket", "grocery", "groceries", "food store", "market")},
    "pharmacy": {"label": "Pharmacy", "types": ["pharmacy"], "words": ("pharmacy", "drugstore", "drug store", "cvs", "walgreens")},
    "transit": {"label": "Bus or train stop", "types": ["transit_station", "bus_station", "subway_station", "train_station"],
                "words": ("bus", "metro", "train", "subway", "transit", "station")},
}

_cache, _cache_lock = {}, threading.Lock()
_places_seen = {}  # place id -> location, so the route endpoint only routes to places a search returned


def _key():
    return os.environ.get("GOOGLE_MAPS_SERVER_API_KEY", "").strip()


def parse_request(prompt, overrides=None):
    """Pull the filters out of a sentence with keyword rules. Form fields in `overrides` win."""
    text = (prompt or "").lower().replace(",", "")
    filters = {"location": "Blacksburg" if area_for(prompt) == "Blacksburg" else "Northern Virginia", "area": area_for(prompt), "max_rent": None,
               "amenity": "supermarket", "max_walk_minutes": 15, "strict": True, "bedrooms": None, "senior": False}
    money = re.search(r"(?:under|below|less than|at most|max(?:imum)?|up to|no more than|<)\s*\$?\s*(\d+(?:\.\d+)?)\s*(k)?", text) \
        or re.search(r"\$\s*(\d+(?:\.\d+)?)\s*(k)?", text)
    if money:
        filters["max_rent"] = float(money.group(1)) * (1000 if money.group(2) else 1)
    minutes = re.search(r"(\d{1,2})\s*-?\s*(?:min|minute)", text)
    if minutes:
        filters["max_walk_minutes"] = max(1, min(30, int(minutes.group(1))))
    for name, spec in AMENITIES.items():
        if any(w in text for w in spec["words"]):
            filters["amenity"] = name
            break
    if re.search(r"\b(preferably|ideally|if possible|nice to have|would be nice|bonus)\b", text):
        filters["strict"] = False
    beds = re.search(r"\b(\d)\s*(?:br|bed|bedroom)", text)
    if beds:
        filters["bedrooms"] = int(beds.group(1))
    elif "studio" in text:
        filters["bedrooms"] = 0
    if re.search(r"\b(senior|62\+?|55\+|elderly|older adult)", text):
        filters["senior"] = True
    for k, v in (overrides or {}).items():
        if v not in (None, ""):
            filters[k] = v
    if overrides and overrides.get("location"):
        filters["area"] = area_for(overrides["location"])
    return filters


def _post(url, body, field_mask, timeout=12):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": _key(), "X-Goog-FieldMask": field_mask})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _meters_between(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(h))


def _nearby(home, amenity, minutes):
    """Candidate places near a home. A straight-line circle only narrows the search; it's not proof of walkability."""
    radius = min(3000, max(400, minutes * WALK_METERS_PER_MINUTE * 1.15))
    data = _post(PLACES_URL, {
        "includedTypes": AMENITIES[amenity]["types"], "maxResultCount": MAX_PLACES + 2, "rankPreference": "DISTANCE",
        "locationRestriction": {"circle": {"center": home, "radius": radius}}},
        "places.id,places.displayName,places.location,places.formattedAddress,places.businessStatus,places.photos,places.primaryType")
    places = []
    for p in data.get("places", []):
        if p.get("businessStatus") == "CLOSED_PERMANENTLY" or not p.get("location"):
            continue
        if p.get("primaryType") not in AMENITIES[amenity]["types"]:
            continue  # e.g. a dollar store tagged "grocery" isn't a supermarket
        photo = (p.get("photos") or [None])[0]
        places.append({
            "place_id": p["id"], "name": (p.get("displayName") or {}).get("text"), "address": p.get("formattedAddress"),
            "location": p["location"],
            "photo": {"name": photo["name"], "attributions": [{"name": a.get("displayName"), "uri": a.get("uri")} for a in photo.get("authorAttributions", [])]} if photo else None,
        })
        _places_seen[p["id"]] = p["location"]
    return places[:MAX_PLACES]


def _walk_times(home, places):
    """Actual walking duration and distance from Google Routes for each place (None when no route)."""
    if not places:
        return []
    rows = _post(MATRIX_URL, {
        "origins": [{"waypoint": {"location": {"latLng": home}}}],
        "destinations": [{"waypoint": {"location": {"latLng": p["location"]}}} for p in places],
        "travelMode": "WALK"}, "originIndex,destinationIndex,duration,distanceMeters,status,condition")
    times = [None] * len(places)
    for row in rows if isinstance(rows, list) else []:
        i = row.get("destinationIndex")
        if i is not None and row.get("condition") == "ROUTE_EXISTS" and row.get("duration"):
            times[i] = {"seconds": int(str(row["duration"]).rstrip("s")), "meters": row.get("distanceMeters")}
    return times


def _evaluate(listing, filters):
    home = {"latitude": listing["lat"], "longitude": listing["lon"]}
    amenity, minutes = filters["amenity"], filters["max_walk_minutes"]
    cache_key = (listing["id"], amenity, minutes)
    with _cache_lock:
        hit = _cache.get(cache_key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    result = {"route_status": "unavailable", "amenity": None, "options": []}
    try:
        places = _nearby(home, amenity, minutes)
        if not places:
            result["route_status"] = "no_places"
        else:
            times = _walk_times(home, places)
            options = []
            for place, walk in zip(places, times):
                options.append({**place, "walk_seconds": walk["seconds"] if walk else None, "walk_meters": walk["meters"] if walk else None,
                                "straight_line_meters": round(_meters_between(home, place["location"]))})
            routed = sorted([o for o in options if o["walk_seconds"] is not None], key=lambda o: o["walk_seconds"])
            result["options"] = routed + [o for o in options if o["walk_seconds"] is None]
            result["amenity"] = routed[0] if routed else options[0]
            result["route_status"] = "available" if routed else "unavailable"
    except Exception:
        result["route_status"] = "error"
    with _cache_lock:
        _cache[cache_key] = (time.time(), result)
    return result


def _display_rent(listing):
    if isinstance(listing.get("monthly_rent"), (int, float)):
        period = '/person/installment' if listing.get('rent_basis') == 'per_person_installment' else '/person/month' if listing.get('rental_space') == 'room' else '/month'
        return f"From ${listing['monthly_rent']:,.2f}{period}"
    return "Contact provider for current rent"


def search(prompt, overrides=None):
    """Run a walking-distance housing search. Returns results plus warnings; never raises for API problems."""
    filters = parse_request(prompt, overrides)
    if filters["area"] is None:
        return {"error": "Clear House covers Northern Virginia and Blacksburg, VA. Try Blacksburg, Arlington, or Reston."}
    if not _key():
        return {"configured": False, "filters": filters, "results": [],
                "warnings": ["Walking-distance search needs a Google Maps server key (GOOGLE_MAPS_SERVER_API_KEY). See WALKABILITY.md for setup."]}

    catalog_filters = {"types": ["affordable_listing", "rental_listing"], "locations": [filters["area"]],
                       "age": 62 if filters["senior"] else 30, "age_group": 'all' if filters['senior'] else 'general'}
    if filters["max_rent"]:
        catalog_filters["max_budget_per_month"] = filters["max_rent"]
    if filters["bedrooms"] is not None:
        catalog_filters["bedrooms"] = filters["bedrooms"]
    rows = filter_catalog(load_catalog(), catalog_filters)

    warnings, seen, candidates = [], set(), []
    for r in sorted(rows, key=lambda r: r.get("monthly_rent") if isinstance(r.get("monthly_rent"), (int, float)) else 1e9):
        place = (r.get("lat"), r.get("lon")) if r.get("lat") is not None else None
        if place and place in seen:
            continue  # one card per building; floor plans at the same address share their walking time
        if place:
            seen.add(place)
        candidates.append(r)
    missing = [r for r in candidates if r.get("lat") is None]
    if missing:
        warnings.append(f"{len(missing)} matching home(s) have no map coordinates, so walking time can't be checked; they're listed without a walking badge.")
    located = [r for r in candidates if r.get("lat") is not None][:MAX_HOMES]
    if len([r for r in candidates if r.get("lat") is not None]) > MAX_HOMES:
        warnings.append(f"Checked the {MAX_HOMES} lowest-rent homes to keep the search fast; narrow the area or budget to see others.")

    with ThreadPoolExecutor(max_workers=4) as pool:
        evaluated = list(pool.map(lambda r: (r, _evaluate(r, filters)), located))

    limit = filters["max_walk_minutes"] * 60
    label = AMENITIES[filters["amenity"]]["label"].lower()
    results = []
    for listing, walk in evaluated + [(r, {"route_status": "no_coordinates", "amenity": None, "options": []}) for r in missing[:4]]:
        best = walk["amenity"]
        within = bool(best and best.get("walk_seconds") is not None and best["walk_seconds"] <= limit)
        if filters["strict"] and not within:
            continue
        reasons = []
        if filters["max_rent"] and isinstance(listing.get("monthly_rent"), (int, float)):
            reasons.append(f"Starting rent is within ${filters['max_rent']:,.0f}")
        if within:
            reasons.append(f"A {label} is a {round(best['walk_seconds'] / 60)}-minute walk (Google Routes)")
        elif walk["route_status"] == "no_places":
            reasons.append(f"No {label} found nearby")
        availability = listing.get("availability") or {}
        results.append({
            "housing": {
                "id": listing["id"], "name": listing.get("community") or listing.get("name"), "floor_plan": listing.get("floor_plan"),
                "address": listing.get("address"), "jurisdiction": listing.get("jurisdiction"),
                "lat": listing.get("lat"), "lon": listing.get("lon"), "monthly_rent": listing.get("monthly_rent"),
                "monthly_rent_display": _display_rent(listing), "eligibility_summary": listing.get("who_it_serves"),
                "availability_status": availability.get("status"), "official_source_url": listing.get("source_url"),
                "phone": listing.get("phone"), "has_photo": bool(listing.get("photo")), "last_verified": listing.get("last_verified"),
            },
            "nearby_amenity": best, "other_options": walk["options"][1:], "route_status": walk["route_status"],
            "within_limit": within, "match_reasons": reasons,
        })
    sort = (overrides or {}).get("sort") or "best"
    if sort == "rent":
        results.sort(key=lambda x: x["housing"]["monthly_rent"] if isinstance(x["housing"]["monthly_rent"], (int, float)) else 1e9)
    else:
        results.sort(key=lambda x: (not x["within_limit"], (x["nearby_amenity"] or {}).get("walk_seconds") or 1e9) if sort in ("best", "walk") else 0)
    if not results:
        warnings.append(f"No reviewed home in {filters['area']} has a verified {label} within a {filters['max_walk_minutes']}-minute walk"
                        + (f" under ${filters['max_rent']:,.0f}." if filters["max_rent"] else ".")
                        + " Try a longer walk, a higher budget, or treating the walk as a preference.")
    return {"configured": True, "filters": filters, "results": results, "warnings": warnings}


def walking_route(home_lat, home_lon, place_id):
    """Route line for the map, only to a place returned by an earlier search (never to arbitrary input)."""
    dest = _places_seen.get(place_id)
    if not dest or not _key():
        return None
    data = _post(ROUTES_URL, {"origin": {"location": {"latLng": {"latitude": home_lat, "longitude": home_lon}}},
                              "destination": {"location": {"latLng": dest}}, "travelMode": "WALK"},
                 "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline")
    route = (data.get("routes") or [None])[0]
    if not route:
        return None
    return {"polyline": route["polyline"]["encodedPolyline"], "seconds": int(route["duration"].rstrip("s")), "meters": route.get("distanceMeters")}


PHOTO_NAME = re.compile(r"^places/[A-Za-z0-9_-]+/photos/[A-Za-z0-9_-]+$")


def place_photo(name):
    """Bytes and content type of a Google place photo. Only well-formed photo names are fetched."""
    if not PHOTO_NAME.match(name or "") or not _key():
        return None
    url = f"https://places.googleapis.com/v1/{name}/media?maxWidthPx=480&maxHeightPx=360"
    req = urllib.request.Request(url, headers={"X-Goog-Api-Key": _key()})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return resp.read(3_000_000), resp.headers.get("Content-Type", "image/jpeg")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    out = search(" ".join(sys.argv[1:]))
    print(json.dumps(out["filters"] if "filters" in out else out, indent=2))
    for r in out.get("results", []):
        a = r["nearby_amenity"] or {}
        walk = f"{round(a['walk_seconds'] / 60)} min / {a['walk_meters']} m" if a.get("walk_seconds") else r["route_status"]
        print(f"- {r['housing']['name']} ({r['housing']['monthly_rent_display']}) -> {a.get('name')}: {walk}")
    for w in out.get("warnings", []):
        print("!", w)
