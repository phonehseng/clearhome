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

from advisor import CHEAP, LANDMARKS, OUTSIDE, TRIP_DEFAULTS, URGENT, WALK_ASSUMED, area_for, rent_estimate, requirements
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
FILLER_END = re.compile(r"\s+(?:please|thanks|thank you|(?:(?:for|around|about|under|below|less than|up to|max|at most)\s+)+\$?\s*\d[\d,]*.*|"
                        r"\$\s*\d[\d,]*.*|for (?:me|my family|\d+ people).*|with .*)$", re.I)
# A lowercase name still counts as a place when it names a kind of place ("fair oaks mall"), but not a generic one
# ("the metro station") or any one of a kind ("a train station"), which isn't one place to measure from.
KIND = re.compile(r"\b(?:mall|hospital|medical center|library|station|airport|university|college|church|high school|middle school|"
                  r"elementary|community center|rec center|town center|shopping center|plaza|clinic|courthouse|headquarters|hq)\b", re.I)
GENERIC = {"the", "a", "an", "my", "our", "metro", "train", "bus", "subway", "grocery", "local", "nearest", "closest", "big", "new", "public",
           "community", "shopping", "medical", "town", "rec", "high", "middle", "elementary", "main", "city", "county"}
BUDGET = re.compile(r"(?:under|below|around|about|less than|up to|max(?:imum)?|budget(?: is| of)?|afford|\$)\s*\$?\s*(\d{3,5})(?!\d)", re.I)
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
    named = (KIND.search(place) and not re.match(r"(?:a|an|any|some)\b", place, re.I)
             and any(w not in GENERIC and not KIND.fullmatch(w) for w in re.findall(r"[a-z]+", place.lower())))
    if len(place) < 3 or not (STREET.match(place) or known or named or re.search(r"\b[A-Z][A-Za-z]", place)):
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


def outside(text):
    """A place outside the service area ("in Richmond"), but not a street named after one ("Richmond Hwy")."""
    t = re.sub(r"\b\w+\s+(?:hwy|highway|rd|road|st|street|ave|avenue|blvd|boulevard|pike|dr|drive|ln|lane|way)\b", " ", (text or "").lower())
    return bool(re.search(OUTSIDE, t))


BARE_CAMPUS = re.compile(r"(?:the\s+|my\s+)?(?:campus|university|college|uni)", re.I)


def campus_for(place, question, profile=None):
    """A bare "campus" is the campus in the area the person named: Virginia Tech in Blacksburg, George Mason in Fairfax.
    With no area to go on it's None, never a Google search for the word "campus" (that finds a "West Campus" anywhere)."""
    if not BARE_CAMPUS.fullmatch((place or "").strip()):
        return place
    area = area_for(question)
    if area in (None, "Northern Virginia") and isinstance((profile or {}).get("location"), str):
        area = area_for(profile["location"])
    return "virginia tech" if area == "Blacksburg" else "george mason" if area == "Fairfax County" else None


def locate(place):
    """(name, latitude, longitude) for a place inside a service region, or None."""
    key = place.lower()
    if outside(key):
        return ("outside", None, None)
    with _lock:
        if key in _cache:
            return _cache[key]
    found, failed = None, False
    landmark = next((v for k, v in LANDMARKS.items() if re.search(rf"\b{re.escape(k)}\b", key)), None)
    if landmark:
        found = (landmark[3] if len(landmark) > 3 else place.upper() if len(place) <= 4 else place.title(), landmark[1], landmark[2])
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
            found, failed = None, True  # not remembered, so asking again in a minute can work
    if found and not any(_miles(found[1], found[2], lat, lon) <= r for _, lat, lon, r in REGIONS):
        found = ("outside", found[1], found[2])
    if not failed:
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


NEAR_ME = re.compile(r"\bnear (?:me|here|my (?:current )?location|where i am)\b", re.I)


def _coords(profile):
    c = (profile or {}).get("coords")
    if isinstance(c, dict) and all(isinstance(c.get(k), (int, float)) and not isinstance(c.get(k), bool) for k in ("lat", "lon")):
        if -90 <= c["lat"] <= 90 and -180 <= c["lon"] <= 180:
            return round(c["lat"], 3), round(c["lon"], 3)  # about 100 m; never stored
    return None


def answer(question, profile=None, history=None):
    """Text answer for a "near X" or "how far a walk" question, or None if the question isn't one."""
    walk = walk_answer(question, profile, history)
    if walk:
        return walk
    if requirements(question):
        return None  # pets, accessibility, household size...: Gemma checks each home against them
    me = _coords(profile)
    if me and NEAR_ME.search(question or "") and not URGENT.search(question):
        inside = any(_miles(me[0], me[1], lat, lon) <= r for _, lat, lon, r in REGIONS)
        if not inside:
            return ("You look to be outside the areas Clear Home covers (Northern Virginia and Blacksburg). "
                    "For housing help where you are, call 211.")
        return _homes_near("your location", me[0], me[1], question, profile)
    if NEAR_ME.search(question or ""):
        return ("I can look near you if you tap **Near me** above the map and allow location, or tell me a place, "
                "like \"near my office at 1800 Tysons Blvd\".")
    place, vague = extract_place(question)
    if vague == "campus" or (place and BARE_CAMPUS.fullmatch(place)):
        campus = campus_for("campus", question, profile)  # "near campus" in Blacksburg is Virginia Tech
        place, vague = (campus, None) if campus else (None, vague)
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
        return ("That place looks outside the areas Clear Home covers (Northern Virginia and Blacksburg). "
                "For other areas, call 211 for local housing help.")
    return _homes_near(name, lat, lon, question, profile)


def _filters(question, profile):
    """Catalog filters from the question and the find form: age group, budget, room or whole home."""
    profile = profile or {}
    filters = {"types": ["affordable_listing", "rental_listing"], "age": 62 if profile.get("senior") else 30,
               "age_group": "senior" if profile.get("senior") else "general"}
    budget = BUDGET.search((question or "").replace(",", ""))  # "a room near GMU around 1000"
    if budget:
        filters["max_budget_per_month"] = float(budget.group(1))
    elif isinstance(profile.get("budget"), (int, float)) and not isinstance(profile["budget"], bool) and profile["budget"] > 0:
        filters["max_budget_per_month"] = profile["budget"]
    if re.search(r"\b(rooms?|roommates?|shared)\b", question or "", re.I):
        filters["rental_space"] = "room"
    return filters


def _homes_near(name, lat, lon, question, profile):
    filters = _filters(question, profile)
    seen, homes = set(), []
    pool = filter_catalog(load_catalog(), {"types": ["affordable_listing", "rental_listing"]})  # for rent estimates
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
    cheap = bool(CHEAP.search(question or ""))
    if cheap:
        # "Cheapest room near X": lowest listed rent first (estimates after listed rents), nearest breaks ties.
        def price(item):
            d, r = item
            if isinstance(r.get("monthly_rent"), (int, float)):
                return (0, r["monthly_rent"], d)
            est = rent_estimate(r, pool)
            return (1, est["low"], d) if est else (2, 0, d)
        homes = [r for _, r in sorted(homes, key=price)[:MAX_HOMES]]
    else:
        homes = [r for _, r in sorted(homes, key=lambda x: x[0])[:MAX_HOMES]]
    if not homes:
        return (f"I don't have a verified {'room' if filters.get('rental_space') == 'room' else 'home'} within {MAX_MILES} miles of {name}"
                + (f" under ${filters['max_budget_per_month']:,.0f} a month" if filters.get("max_budget_per_month") else "") + " that fits your choices. "
                "Try a higher budget, or call 211 for local housing help.\n\nThis is guidance, not legal advice.")
    commute = _commutes(homes, lat, lon)
    what = "rooms" if filters.get("rental_space") == "room" else "homes"
    limit = f" under ${filters['max_budget_per_month']:,.0f}/month" if filters.get("max_budget_per_month") else ""
    lines = [f"Lowest-rent verified {what}{limit} within {MAX_MILES} miles of {name}:" if cheap else f"Closest verified {what}{limit} to {name}:"]
    bases = {}
    for i, r in enumerate(homes):
        est = None if isinstance(r.get("monthly_rent"), (int, float)) else rent_estimate(r, pool)
        if est:
            bases.setdefault(est["basis"], None)
        per = "/person/month" if r.get("rental_space") == "room" else "/month"
        rent = (f"from ${r['monthly_rent']:,.0f}{per}" if isinstance(r.get("monthly_rent"), (int, float))
                else f"est. ${est['low']:,.0f}–${est['high']:,.0f}/month*" if est else "rent: ask the provider")
        miles = _miles(lat, lon, r["lat"], r["lon"])
        trip = ["at or next to this address" if miles < 0.1 else f"{miles:.1f} mi away"]
        if commute.get(i, {}).get("DRIVE"):
            trip.append(f"about {commute[i]['DRIVE']} min by car")
        if commute.get(i, {}).get("TRANSIT") and miles >= 0.1:
            trip.append(f"{commute[i]['TRANSIT']} min by transit")
        kind = " (regular rental, not income-restricted)" if r.get("type") == "rental_listing" else ""
        phone = f" Call {r['phone']}." if r.get("phone") else ""
        lines.append(f"- **{r.get('community') or r['name']}**{kind}: {rent}; {', '.join(trip)}.{phone}")
    if bases:
        lines.append(f"* Estimated from {' and '.join(bases)}: these homes don't publish rents, so ask the provider for the real price.")
    lines.append(("Commute times are from Google and change with traffic and schedules. " if commute else "Distances are straight-line. ")
                 + "Advertised rents and openings aren't guaranteed, so confirm with the property.\n\nThis is guidance, not legal advice.")
    return "\n".join(lines)


# ---- "How far a walk is it?" --------------------------------------------------------------------------------
# "are these at least 13 minutes' walk from Virginia Tech", "rooms within a 10 minute walk of VT campus".
# Walking times come from Google Routes (WALK); without a key they're estimated from distance and labeled so.
WALK = re.compile(r"\bwalk(?:s|ing|able)?\b", re.I)
WALK_FROM = re.compile(r"\bwalk(?:s|ing|able)?\b(?:\s+(?:time|distance))?.*?\b(?:from|to|of)\s+(?:the\s+)?(.+?)(?:[?!]|\.(?:\s|$)|$)", re.I)
MINUTES = re.compile(r"\b(\d{1,3})\s*-?\s*(?:min(?:ute)?s?)\b", re.I)
AT_LEAST = re.compile(r"\b(?:at least|more than|over|longer than|farther than|further than|no closer than|minimum)\b", re.I)
THESE = re.compile(r"\b(?:these|those|them|they|each|any of (?:them|these)|the (?:ones|places|listings|homes|rooms|apartments) (?:you|above))\b", re.I)
WALK_MILES = 3  # beyond this nobody walks; homes farther away are left out of a "within N minutes" search
MINUTES_PER_MILE = 25  # ~3 mph with a 1.25 street-detour factor, only when Google can't give a real walking time


def _walk_minutes(homes, lat, lon):
    """{index: minutes} walking from each home to the place (Google Routes), or {} if unavailable."""
    if not _key() or not homes:
        return {}
    out = {}
    for start in range(0, len(homes), 25):  # the matrix takes at most 25 origins per call
        batch = homes[start:start + 25]
        try:
            rows = _post(MATRIX_URL, {"origins": [{"waypoint": {"location": {"latLng": {"latitude": h["lat"], "longitude": h["lon"]}}}} for h in batch],
                                      "destinations": [{"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lon}}}}],
                                      "travelMode": "WALK"}, "originIndex,duration,condition")
        except Exception:
            return {}
        for row in rows if isinstance(rows, list) else []:
            if row.get("condition") == "ROUTE_EXISTS" and row.get("duration"):
                out[start + row["originIndex"]] = round(int(str(row["duration"]).rstrip("s")) / 60)
    return out


def _named_in(text, rows):
    """Verified homes the previous answer named, in the order it named them (one per community)."""
    low, found = (text or "").casefold(), []
    for r in rows:
        if r.get("lat") is None:
            continue
        names = [n for n in (r.get("name"), r.get("community")) if n]
        hits = [low.find(n.casefold()) for n in names if len(n) > 3 and n.casefold() in low]
        if hits:
            found.append((min(hits), r))
    seen, out = set(), []
    for _, r in sorted(found, key=lambda x: x[0]):
        key = (r.get("community") or r["name"]).casefold()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def walk_answer(question, profile=None, history=None):
    """Walking times between homes and a place, or None if the question isn't about walking to a place."""
    if not WALK.search(question or "") or URGENT.search(question):
        return None
    if requirements(question):
        return None  # "furnished, under $1000, a 13 minute walk from campus": Gemma checks it all, with walking times added

    m = WALK_FROM.search(question)
    if not m:
        return None
    place = FILLER_END.sub("", re.split(r"\s+(?:from|to)\s+|[,;]", m.group(1).strip())[0])
    place = re.sub(r"\b(?:campus|area)\b$", lambda x: "campus" if re.search(r"\bvt\b", place, re.I) else "", place, flags=re.I).strip() or place
    if NOT_A_PLACE.match(place) or WORKPLACE.match(place) and not place[WORKPLACE.match(place).end():].strip() and not BARE_CAMPUS.fullmatch(place):
        return None
    place = campus_for(place, question, profile)
    if not place:
        return None  # "walking range of campus" with no area: Gemma's walk check (or the which-campus question) handles it
    found = locate(place)
    if not found:
        return None
    name, lat, lon = found
    if name == "outside":
        return ("That place looks outside the areas Clear Home covers (Northern Virginia and Blacksburg). "
                "For other areas, call 211 for local housing help.")
    limit = MINUTES.search(question)
    limit = int(limit.group(1)) if limit and 0 < int(limit.group(1)) <= 180 else None
    at_least = bool(limit and AT_LEAST.search(question))
    rows = filter_catalog(load_catalog(), {"types": ["affordable_listing", "rental_listing"]})
    earlier = next((t.get("text") for t in reversed(history or []) if t.get("role") == "assistant"), "")
    # Homes named in the question itself ("from Union Blacksburg"), else the ones the last answer listed ("are these ...").
    homes = [r for r in _named_in(question, rows) if place.casefold() not in (r.get("community") or r["name"]).casefold()]
    if not homes and THESE.search(question):
        homes = _named_in(earlier, rows)
    follow_up = bool(homes)
    if not follow_up:
        # A fresh question: every verified home that fits the filters within walking range of the place.
        seen = set()
        for r in filter_catalog(load_catalog(), _filters(question, profile)):
            key = (r.get("community") or r["name"]).casefold()
            if r.get("lat") is not None and key not in seen and _miles(lat, lon, r["lat"], r["lon"]) <= WALK_MILES:
                seen.add(key)
                homes.append(r)
        homes.sort(key=lambda r: _miles(lat, lon, r["lat"], r["lon"]))
        homes = homes[:25]
    # "Walking distance" with no time is the standard 15-minute walk (said at the end); a follow-up with no time just
    # lists the walking times it asked about.
    assumed = limit is None and not follow_up
    limit = TRIP_DEFAULTS["WALK"] if assumed else limit
    if not homes:
        return (f"None of the verified homes that fit your choices is within a {limit or TRIP_DEFAULTS['WALK']}-minute walk of {name}. "
                "Try a longer walk, a bus or a nearby town, or call 211 for local housing help."
                + (f"\n{WALK_ASSUMED}" if assumed else "") + "\n\nThis is guidance, not legal advice.")
    walked = _walk_minutes(homes, lat, lon)
    timed = []
    for i, r in enumerate(homes):
        miles = _miles(lat, lon, r["lat"], r["lon"])
        timed.append((walked.get(i, round(miles * MINUTES_PER_MILE)), i in walked, miles, r))
    timed.sort(key=lambda t: t[0])
    # A straight-line estimate never makes a home "within" a walk: only a measured Google route can.
    fits = lambda minutes, real: minutes >= limit if at_least else real and minutes <= limit
    if limit:
        ok = [t for t in timed if fits(t[0], t[1])]
        rule = f"at least a {limit}-minute walk from" if at_least else f"within a {limit}-minute walk of"
        if not at_least and not walked:
            head = (f"Google walking routes aren't available right now, so I can't verify which homes are {rule} {name}. "
                    "Straight-line estimates only, not measured walks:")
        elif follow_up:
            some = "it is" if len(timed) == 1 else f"all {len(timed)} are"
            head = (f"Yes, {some} {rule} {name}." if len(ok) == len(timed) else
                    f"No, {'it is not' if len(timed) == 1 else 'none of them is'} {rule} {name}." if not ok else
                    f"{len(ok)} of the {len(timed)} are {rule} {name}.")
        else:
            head = (f"Verified homes {rule} {name}:" if ok else
                    f"None of the verified homes that fit your choices is {rule} {name}. Closest by walking route:")
        shown = timed if follow_up else ok[:8] if ok else timed[:3]  # none fit: just the three closest
    else:
        head, shown = f"Walking times {'from' if follow_up else 'to'} {name}:", timed[:8]
    lines = [head]
    for minutes, real, miles, r in shown:
        mark = " ✓" if limit and follow_up and fits(minutes, real) else " ✗" if limit and follow_up and (real or at_least) else ""  # marks only answer a yes/no follow-up
        per = "/person/month" if r.get("rental_space") == "room" else "/month"
        rent = f"; from ${r['monthly_rent']:,.0f}{per}" if isinstance(r.get("monthly_rent"), (int, float)) else ""
        lines.append(f"- **{r.get('community') or r['name']}**: about {minutes} min walk{'' if real else ' (estimated)'}, {miles:.1f} mi{rent}{mark}")
    lines.append(("Walking times are from Google Maps." if walked else
                  f"Walking times are estimated from straight-line distance (about {MINUTES_PER_MILE} minutes a mile on streets), "
                  "so check the route on the map.")
                 + (" Campus is big, so your building can add or save several minutes." if re.search(r"universit|college|campus|virginia tech|george mason", name, re.I) else "")
                 + (f"\n{WALK_ASSUMED}" if assumed else "") + "\n\nThis is guidance, not legal advice.")
    return "\n".join(lines)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    t = time.time()
    print(answer(" ".join(sys.argv[1:])) or "(not a near-place question)")
    print(f"\n[{time.time() - t:.1f}s]")
