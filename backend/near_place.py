"""Homes close to a place people go to: a store ("close to walmart"), a campus, an employer, a landmark, an address.

No AI. A keyword script reads the place and the trip ("close" means a walk unless they say drive or bus). A chain name
is not one place: Google Places finds the real stores nearest the town they name (or the find form's area, or one said
earlier in the chat), and with no town at all the chat asks which store first. Google Routes then measures the trip
from each verified home, and only measured trips within the limit count as close. Straight-line distance only narrows
which homes get routed; it is never shown as a walk, and a home Google can't route is never called close.

Usage: python backend/near_place.py "give me something close to walmart in blacksburg"
"""
import difflib
import os
import re
import sys
import threading
import time
from urllib.parse import quote

import nearby
from advisor import AREAS, CHEAP, PLACE_MARK, TRIP_DEFAULTS, URGENT, WALK_ASSUMED, Instant, rent_estimate, requirements
from catalog import filter_catalog, load_catalog

# Chains people name as a place to live near. Each is many stores, never one place. (name, spellings people type)
CHAINS = [("Walmart", r"wal+[- ]?m[ae]rts?|wal+[- ]?mat|walmart's"), ("Target", r"targets?|target's"), ("Costco", r"cost?cos?|costco's"),
          ("Kroger", r"krogers?|kroger's"), ("Food Lion", r"food ?lions?"), ("Giant", r"giant(?: foods?)?"), ("Safeway", r"safeways?"),
          ("Aldi", r"aldis?|aldi's"), ("Lidl", r"lidls?"), ("Wegmans", r"wegmans?|wegman's"), ("Harris Teeter", r"harris ?teeters?"),
          ("Trader Joe's", r"trader joe'?s"), ("Whole Foods", r"whole ?foods?"), ("Sprouts", r"sprouts"), ("Publix", r"publix"),
          ("Home Depot", r"home ?depot"), ("Lowe's", r"lowe'?s"), ("CVS", r"cvs"), ("Walgreens", r"walgreens?|walgreen's"),
          ("Rite Aid", r"rite ?aid"), ("Dollar General", r"dollar general"), ("Dollar Tree", r"dollar tree"), ("Food City", r"food city"),
          ("Sam's Club", r"sam'?s club"), ("BJ's", r"bj'?s(?: wholesale)?"), ("Best Buy", r"best ?buy"), ("IKEA", r"ikea"),
          ("Starbucks", r"starbucks?"), ("Planet Fitness", r"planet fitness")]
# Kinds of places ("a market", "a grocery store"): many stores of any brand, matched by Google's place type, and only ones
# close to the town they named. (name, spellings people type, Google place types, plural)
KINDS = [("grocery store", r"grocer(?:y|ies)(?: stores?)?|supermarkets?|food (?:stores?|markets?)|markets?", {"supermarket", "grocery_store", "market"}, "grocery stores"),
         ("pharmacy", r"pharmac(?:y|ies)|drug ?stores?", {"pharmacy", "drugstore"}, "pharmacies"),
         ("gym", r"gyms?|fitness (?:centers?|clubs?)", {"gym", "fitness_center"}, "gyms"),
         ("coffee shop", r"coffee ?shops?|cafes?", {"cafe", "coffee_shop"}, "coffee shops")]
KIND_TYPES = {name: types for name, _, types, _ in KINDS}
KIND_MILES = 4  # a grocery store "in Reston" is one near Reston, not the nearest one with "market" in its name
CHAINS = CHAINS + [(name, pattern) for name, pattern, _, _ in KINDS]


def _many(chain):
    """'Walmart stores', 'grocery stores'."""
    return next((plural for name, _, _, plural in KINDS if name == chain), f"{chain} stores")
_NORM = lambda s: re.sub(r"[^a-z]", "", s.lower())
_FUZZY = {_NORM(name): name for name, _ in CHAINS if len(_NORM(name)) >= 5}  # "walmrat"; never short ones ("aldie" is a town)
# Google also lists offices and departments under a brand ("Walmart Labs"); only places people shop or visit count.
STORE_TYPES = {"supermarket", "pharmacy", "drugstore", "market", "cafe", "coffee_shop", "gym", "fitness_center", "shopping_mall", "store"}

# Words that put a place right after them: "close to walmart", "walking distance from the walmart on richmond hwy".
CUE = (r"(?:near(?:by)?|close (?:to|by)|closer to|closest to|next to|by|beside|around|across from|not far from|"
       r"(?:walking|driving) distance (?:to|of|from)|walk(?:ing|able)? (?:to|from)|walk of|drive (?:to|from|of)|driving (?:to|from)|"
       r"(?:ride|trip|commute) (?:to|from|of)|(?:bus|train|metro|car|transit) (?:ride )?(?:to|from)|min(?:ute)?s? (?:from|to|of|away from)|"
       r"within [\w.$ -]{1,24}? (?:of|from))")
DET = r"(?:(?:the|a|an|any|some|one|my|our|local|nearest|closest|nearby|same|that|this)\s+)*"
CHAIN = re.compile(rf"\b{CUE}\s+{DET}((?:{'|'.join(p for _, p in CHAINS)}))\b(.*)", re.I)
WORD = re.compile(rf"\b{CUE}\s+{DET}([a-z][a-z'-]{{3,}})(?:\s+([a-z][a-z'-]+))?\b(.*)", re.I)
# For other places, only words that claim closeness switch to walking; "near my office" keeps its commute answer (nearby.py).
CLOSE = re.compile(r"\b(?:close (?:to|by)|closer to|closest to|next to|(?:in )?walking distance)\b", re.I)
THAT = re.compile(r"\b(?:that|this|the same) (?:store|shop|one|place|location|branch|spot)\b|\b(?:from|to|near) there\b", re.I)
OURS = re.compile(r"\d+-minute (?:walk|drive|bus or train trip) of\b")  # how this module's answers say their limit

DRIVE = re.compile(r"\b(?:driv(?:e|es|ing)|by car|car ride)\b", re.I)
TRANSIT = re.compile(r"\b(?:by (?:bus|metro|train|transit)|bus ride|on the bus|public transit|transit (?:ride|trip|time))\b", re.I)
RANGE = re.compile(r"\b(\d{1,3})\s*(?:-|–|to)\s*(\d{1,3})\s*-?\s*min", re.I)
MINUTES = re.compile(r"\b(\d{1,3})\s*-?\s*min(?:ute)?s?\b|\b(half an hour|an hour)\b", re.I)
MILES = re.compile(r"\b(\d+(?:\.\d+)?|a|one|half a)\s*-?\s*(?:mi|miles?)\b", re.I)
# A walk is what "close" means unless they say otherwise; the answer always says which limit it used.
DEFAULT_MINUTES = TRIP_DEFAULTS  # the same standard as every other answer (advisor.py)
MODE_WORD = {"WALK": "walk", "DRIVE": "drive", "TRANSIT": "bus or train trip"}
ROUTE_WORD = {"WALK": "walking", "DRIVE": "driving", "TRANSIT": "transit"}
# Generous top speeds (metres a minute) for the straight-line prefilter, so it never drops a home a route could reach.
REACH = {"WALK": 100, "DRIVE": 1600, "TRANSIT": 1000}
MAX_STORES = 3     # stores per answer; homes are matched to the nearest of them
MAX_ROUTED = 25    # homes per route matrix call (25 homes x 3 stores stays inside Google's per-call limits)
MAX_SHOWN = 5
CACHE_SECONDS = 6 * 3600
_cache, _lock = {}, threading.Lock()


def _cached(key, make):
    """Places and route results for a few hours. Failures (None) aren't kept, so asking again can succeed."""
    with _lock:
        hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    value = make()
    if value is not None:
        with _lock:
            if len(_cache) > 300:  # keyed partly on what people type, so keep it bounded
                _cache.clear()
            _cache[key] = (time.time(), value)
    return value


def _chain(text):
    """(chain name, the words after it) for "close to walmart in reston", typos included, or None."""
    m = CHAIN.search(text)
    if m:
        return next(name for name, p in CHAINS if re.fullmatch(p, m.group(1), re.I)), m.group(2)
    for m in WORD.finditer(text):
        first, second, rest = m.group(1), m.group(2) or "", m.group(3)
        for phrase, after in (((first + second), rest), (first, f" {second}{rest}")):
            hit = difflib.get_close_matches(_NORM(phrase), _FUZZY, n=1, cutoff=0.8)
            if hit:
                return _FUZZY[hit[0]], after
    return None


def _trip(text):
    """(mode, minutes or None, metres or None, at_least) from "a 10 minute walk", "10-15 min", "a short drive", "within 1 mile"."""
    mode = "WALK"
    for part in text.split(" (earlier in this chat: "):  # newest words first: "walk instead" wins over an earlier "drive"
        said = "DRIVE" if DRIVE.search(part) else "TRANSIT" if TRANSIT.search(part) else "WALK" if re.search(r"\bwalk", part, re.I) else None
        if said:
            mode = said
            break
    span, m = RANGE.search(text), MINUTES.search(text)
    minutes = int(span.group(2)) if span else (int(m.group(1)) if m.group(1) else 30 if "half" in m.group(2).lower() else 60) if m else None
    minutes = minutes if minutes and 0 < minutes <= 180 else None
    miles = MILES.search(text)
    metres = None
    if miles and not minutes:
        n = miles.group(1).lower()
        metres = round((1 if n in ("a", "one") else 0.5 if n == "half a" else float(n)) * 1609.34)
        if metres > 4828:  # farther than 3 miles is a drive, not a walk
            mode = "DRIVE" if mode == "WALK" else mode
    return mode, minutes, metres, bool((minutes or metres) and nearby.AT_LEAST.search(text))


def _merge(question, earlier):
    return f"{question} (earlier in this chat: {earlier})"


def read(question, history=None):
    """What a near-a-place question asks for, or None when it isn't one:
    {"chain", "hint", "place", "mode", "minutes", "metres", "at_least", "stated", "text", "reply"}."""
    text = (question or "").replace("’", "'")
    if not text.strip() or URGENT.search(text):
        return None
    found = _destination(text)
    if not found:
        # "what about a 25 minute walk from that store?": the place is the one asked about earlier in the chat.
        last = next((t.get("text", "") for t in reversed(history or []) if t.get("role") == "assistant"), "")
        if THAT.search(text) or (OURS.search(last) and (MINUTES.search(text) or DRIVE.search(text) or TRANSIT.search(text) or re.search(r"\bwalk", text, re.I))):
            for turn in reversed(history or []):
                if turn.get("role") == "user" and _destination(turn.get("text", "")):
                    text = _merge(text, turn["text"])
                    found = _destination(text)
                    break
    if not found:
        return None
    reply = text.split(" (earlier in this chat: ", 1)[0] if " (earlier in this chat: " in text else ""
    mode, minutes, metres, at_least = _trip(text)
    return {**found, "mode": mode, "minutes": minutes or (None if metres else DEFAULT_MINUTES[mode]), "metres": metres,
            "at_least": at_least, "stated": bool(minutes or metres), "text": text, "reply": reply}


def _destination(text):
    chain = _chain(text)
    if chain:
        return {"chain": chain[0], "hint": chain[1], "place": None}
    if CLOSE.search(text):
        place, vague = nearby.extract_place(text)
        if place and not vague:
            return {"chain": None, "hint": "", "place": place}
    return None


# ---- Which store: a chain name needs a town or a street ------------------------------------------------------
STREETISH = re.compile(r"\d|\b(?:st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|ln|lane|pike|hwy|highway|way|pkwy|parkway|"
                       r"plaza|mall|center|centre|crossing|square|route|rt)\b", re.I)
HINT_NOISE = re.compile(r"\b(?:\d{1,3}\s*(?:-|–|to)?\s*(?:\d{1,3}\s*)?-?\s*min(?:ute)?s?|\d+(?:\.\d+)?\s*(?:mi|miles?))\b.*|"
                        r"\b(?:under|below|less than|up to|max|at most|around|about|for|with|that|which|and|so|but|please|thanks)\b.*|\$.*|"
                        r"\b(?:walk\w*|driv\w*|by car|by bus|close|near|is|it's|its|the one|one|store|location|branch|yes|yeah|ok|okay|i mean|"
                        r"in|on|at|off|by|the|a|an|of|to|there|is fine|works|please)\b", re.I)
STOP_TOKENS = {"in", "on", "at", "the", "a", "an", "of", "to", "by", "near", "va", "virginia", "and"}


def _clean_hint(text):
    """'on richmond hwy, 10 minutes is fine' -> 'richmond hwy'."""
    t = re.split(r"[.?!;()]|,", text or "", maxsplit=1)[0]
    return " ".join(HINT_NOISE.sub(" ", re.sub(r"[^\w\s'&-]", " ", t)).split())


def _town(text):
    """('christiansburg', 'Blacksburg') for the first town or area named, or ('northern virginia', ...) when only the region is."""
    t, best = (text or "").lower(), None
    for word, area in AREAS:
        m = re.search(rf"\b{re.escape(word)}\b", t)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), word, area)
    if best:
        return best[1], best[2]
    if re.search(r"\b(?:northern virginia|northern va|nova)\b", t):
        return "northern virginia", "Northern Virginia"
    return None


def _region(area):
    return nearby.REGIONS[1] if area == "Blacksburg" else nearby.REGIONS[0]


def _brand(name, chain, types=()):
    if chain in KIND_TYPES:  # a kind of place: any brand, by its Google type
        return bool(set(types) & KIND_TYPES[chain])
    return _NORM(chain).rstrip("s") in _NORM(name)  # "Lowe's Home Improvement", "Wal-Mart Supercenter"


def _stores_search(query, center, radius_m, chain):
    """Open stores of the chain from Google Places Text Search: [{name, address, lat, lon, place_id}], or None on failure."""
    def run():
        try:
            data = nearby._post(nearby.PLACES_TEXT_URL, {"textQuery": query, "maxResultCount": 8,
                                                         "locationBias": {"circle": {"center": {"latitude": center[0], "longitude": center[1]}, "radius": radius_m}}},
                                "places.id,places.displayName,places.formattedAddress,places.location,places.businessStatus,places.types")
        except Exception:
            return None
        out = []
        for p in data.get("places") or []:
            name = (p.get("displayName") or {}).get("text") or ""
            types = set(p.get("types") or [])
            if not p.get("location") or p.get("businessStatus") in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY") or not _brand(name, chain, types):
                continue
            if not (types & STORE_TYPES or any(t.endswith("_store") for t in types)):
                continue  # "Walmart Labs" is an office
            lat, lon = p["location"]["latitude"], p["location"]["longitude"]
            if not any(nearby._miles(lat, lon, rlat, rlon) <= r for _, rlat, rlon, r in nearby.REGIONS):
                continue
            if any(nearby._miles(lat, lon, s["lat"], s["lon"]) < 0.1 for s in out):
                continue  # the pharmacy or garden center of a store already listed
            out.append({"name": name, "address": (p.get("formattedAddress") or "").replace(", USA", ""), "lat": lat, "lon": lon, "place_id": p.get("id")})
        return out
    return _cached(("stores", query.lower(), round(center[0], 2), round(center[1], 2)), run)


def _ask(chain, want, broad=False):
    text = (f"Northern Virginia has many {_many(chain)}. " if broad else "") + f"Which {chain}, {PLACE_MARK} A town (like Christiansburg or Reston) or a street (like Richmond Hwy) is enough."
    if not want["stated"] and want["mode"] == "WALK":
        text += " And is a 10–15 minute walk what you mean by close?"
    return Instant(text)


def resolve(want, profile=None, history=None):
    """Where they mean: {"stores": [...], "label": text} or {"say": text} (a question to ask, or why it can't be found)."""
    if want["chain"] is None:
        return _resolve_place(want)
    chain = want["chain"]
    hint = " ".join(filter(None, (_clean_hint(want["hint"]), _clean_hint(want["reply"]))))
    town = _town(hint) or _town(want["text"])
    if not town:
        location = (profile or {}).get("location")  # the find form's area
        if isinstance(location, str) and location.strip():
            area = nearby.area_for(location)
            town = _town(location) or ((location.strip().lower(), area) if area and area != "Northern Virginia" else None)
    for turn in reversed(history or []):  # an area said earlier in the chat ("cheap rooms in blacksburg")
        if town:
            break
        if turn.get("role") == "user":
            town = _town(turn.get("text", ""))
    if not town and nearby.outside(hint + " " + want["text"]):
        return {"say": "That place looks outside the areas Clear Home covers (Northern Virginia and Blacksburg). For other areas, call 211 for local housing help."}
    street = hint
    for word, _ in AREAS + [("northern virginia", None), ("nova", None), ("virginia", None), ("va", None)]:
        street = re.sub(rf"\b{re.escape(word)}\b", " ", street, flags=re.I)
    street = " ".join(street.split())
    # Only words that name a place count ("on richmond hwy", "in kingstowne", or a reply to "which store?"), not "walmart lol".
    if street and not (STREETISH.search(street) or want["reply"] or re.search(r"\b(?:in|on|at|off|near|by|around)\s+\w", want["hint"], re.I)):
        street = ""
    if not town and not street:
        return {"say": _ask(chain, want)}
    if not nearby._key():
        return {"say": f"I can't look up {chain} stores right now (Google Maps isn't set up here), so I can't tell which homes are close to one. "
                       "Try the map's \"Live near a…\" search, or call 211 for local housing help."}
    region = _region(town[1] if town else nearby.area_for(street))
    if street:
        # A specific store: "the walmart on richmond hwy", "walmart at 2400 n franklin st". Two on one road are both kept.
        query = f"{chain} {street}" + (f" {town[0]}" if town and town[0] != "northern virginia" else "") + ", VA"
        stores = _stores_search(query, region[1:3], 50000.0, chain)
        if stores:
            words = {w for w in re.findall(r"[a-z0-9]+", street.lower()) if w not in STOP_TOKENS}
            score = lambda s: len(words & set(re.findall(r"[a-z0-9]+", f"{s['name']} {s['address']}".lower())))
            top = max(score(s) for s in stores)
            stores = [s for s in stores if score(s) == top][:MAX_STORES] if top else stores[:1]
        where = f"matching \"{street}\""
    else:
        if town[1] == "Northern Virginia":
            return {"say": _ask(chain, want, broad=True)}
        center = nearby.locate(f"{town[0]}, VA")
        center = (center[1], center[2]) if center and center[0] != "outside" else region[1:3]
        stores = _stores_search(f"{chain} near {town[0]}, VA", center, 20000.0, chain)
        if stores:
            stores = sorted(stores, key=lambda s: nearby._miles(center[0], center[1], s["lat"], s["lon"]))
            near = KIND_MILES if chain in KIND_TYPES else nearby.MAX_MILES
            stores = [s for s in stores if nearby._miles(center[0], center[1], s["lat"], s["lon"]) <= near][:MAX_STORES]
        where = f"nearest {town[0].title()}"
    if stores is None:
        return {"say": f"I couldn't reach Google Maps to find the {chain} just now, so I can't tell which homes are close to it. Please ask again in a minute."}
    if not stores:
        return {"say": Instant(f"I couldn't find a {chain} {where.replace('nearest', 'near')} on Google Maps. Which {chain}, {PLACE_MARK}")}
    if len(stores) == 1:
        label = (f"The {chain} {where} is " if not street else "") + f"{stores[0]['name']}, {stores[0]['address']}"
    else:
        label = f"The {len(stores)} {_many(chain)} {where}: " + "; ".join(f"{s['name']}, {s['address']}" for s in stores)
    return {"stores": stores, "label": label, "chain": chain}


def _resolve_place(want):
    """A single named place, campus, employer or address (nearby.locate: the Census geocoder or Google Places)."""
    place = want["place"]
    reply = _clean_hint(want["reply"])
    found = nearby.locate(f"{place} {reply}".strip() if reply else place)
    if found and found[0] == "outside":
        return {"say": "That place looks outside the areas Clear Home covers (Northern Virginia and Blacksburg). For other areas, call 211 for local housing help."}
    if not found:
        return {"say": Instant(f"I couldn't find \"{place}\" on the map. What's its street address, {PLACE_MARK}")}
    return {"stores": [{"name": found[0], "address": "", "lat": found[1], "lon": found[2], "place_id": None}], "label": found[0], "chain": None}


# ---- Measuring the trip from each home ------------------------------------------------------------------------
def _homes(text, profile=None):
    """Verified homes that fit the budget, room-or-home, bedroom and age choices: one per community (its lowest rent)."""
    profile = dict(profile or {})
    if re.search(r"\b62 or older\b|\bseniors?\b", text or "", re.I):
        profile["senior"] = True
    filters = nearby._filters(text, profile)
    beds = re.search(r"\b(\d)\s*-?\s*(?:br|bed|beds|bedrooms?)\b", text or "", re.I)
    if beds:
        filters["bedrooms"] = int(beds.group(1))
    elif re.search(r"\bstudio\b", text or "", re.I):
        filters["bedrooms"] = 0
    pool = filter_catalog(load_catalog(), filters)
    cap = filters.get("max_budget_per_month")
    if cap:  # homes that don't publish a rent stay in when our estimate starts within the budget (the answer says it's an estimate)
        loose = {k: v for k, v in filters.items() if k != "max_budget_per_month"}
        seen = {r["id"] for r in pool}
        pool += [r for r in filter_catalog(load_catalog(), loose) if r["id"] not in seen and not isinstance(r.get("monthly_rent"), (int, float))
                 and (rent_estimate(r) or {}).get("low", float("inf")) <= cap]
    best = {}
    for r in pool:
        if r.get("lat") is None:
            continue
        key = (r.get("community") or r["name"]).casefold()
        rent = r["monthly_rent"] if isinstance(r.get("monthly_rent"), (int, float)) else float("inf")
        if key not in best or rent < best[key][0]:
            best[key] = (rent, r)
    return [r for _, r in best.values()]


def _routes(homes, stores, mode):
    """{home index: (seconds, metres, store index)}: each home's quickest Google route to any of the stores.
    Homes with no route are left out. None when Google Routes couldn't be reached."""
    if not homes:
        return {}
    if not nearby._key():
        return None
    def run():
        point = lambda lat, lon: {"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lon}}}}
        try:
            rows = nearby._post(nearby.MATRIX_URL, {"origins": [point(h["lat"], h["lon"]) for h in homes],
                                                    "destinations": [point(s["lat"], s["lon"]) for s in stores], "travelMode": mode},
                                "originIndex,destinationIndex,duration,distanceMeters,condition")
        except Exception:
            return None
        if not isinstance(rows, list):
            return None
        best = {}
        for row in rows:
            if row.get("condition") != "ROUTE_EXISTS" or not row.get("duration"):
                continue  # no route found: unknown, never "close"
            i, j = row.get("originIndex", 0), row.get("destinationIndex", 0)
            seconds = int(str(row["duration"]).rstrip("s"))
            if i not in best or seconds < best[i][0]:
                best[i] = (seconds, row.get("distanceMeters", 0), j)
        return best
    return _cached(("routes", mode, tuple(h["id"] for h in homes), tuple((s["lat"], s["lon"]) for s in stores)), run)


def measure(found, want, profile=None):
    """Route the homes that could possibly be within the limit, then keep only the measured trips that are."""
    stores, mode = found["stores"], want["mode"]
    homes = _homes(want["text"], profile)
    gap = {h["id"]: min(nearby._miles(h["lat"], h["lon"], s["lat"], s["lon"]) for s in stores) for h in homes}
    ranked = sorted(homes, key=lambda h: (gap[h["id"]], h["id"]))
    if want["at_least"]:
        pool = [h for h in ranked if gap[h["id"]] <= nearby.MAX_MILES][:MAX_ROUTED]
    else:
        reach = want["metres"] * 1.1 if want["metres"] else want["minutes"] * REACH[mode]
        pool = [h for h in ranked if gap[h["id"]] * 1609.34 <= reach][:MAX_ROUTED]
    routes = _routes(pool, stores, mode)
    out = {"pool": pool, "routes": routes, "matches": [], "over": [], "nearest": [h for h in ranked if gap[h["id"]] <= nearby.MAX_MILES][:3]}
    if routes is None:
        return out
    def ok(seconds, metres):
        if want["metres"]:
            return metres >= want["metres"] if want["at_least"] else metres <= want["metres"]
        return seconds >= want["minutes"] * 60 if want["at_least"] else seconds <= want["minutes"] * 60
    rent = lambda h: h["monthly_rent"] if isinstance(h.get("monthly_rent"), (int, float)) else float("inf")
    for i, h in enumerate(pool):
        if i in routes:
            seconds, metres, j = routes[i]
            (out["matches"] if ok(seconds, metres) else out["over"]).append((seconds, metres, j, h))
    cheap = bool(CHEAP.search(want["text"]))
    # Quickest trip first (lowest rent first for "cheapest"); the name breaks ties so the order never shuffles.
    out["matches"].sort(key=lambda t: (rent(t[3]), t[0], t[3]["name"]) if cheap else (t[0], rent(t[3]), t[3]["name"]))
    out["over"].sort(key=lambda t: (rent(t[3]), t[0], t[3]["name"]) if cheap else (t[0], t[3]["name"]))  # "cheapest": lowest rent first here too
    if not want["at_least"] and not want["metres"]:  # a 190-minute walk isn't a useful "almost": up to twice the limit only
        out["over"] = [t for t in out["over"] if t[0] <= 2 * want["minutes"] * 60]
    if not out["matches"] and not out["over"] and mode == "WALK" and out["nearest"]:
        # Nothing within walking reach: the closest homes by car, clearly labeled as the broader option.
        drive = _routes(out["nearest"], stores, "DRIVE") or {}
        out["by_car"] = sorted(((drive[i][0], drive[i][1], drive[i][2], h) for i, h in enumerate(out["nearest"]) if i in drive), key=lambda t: (t[0], t[3]["name"]))
    return out


# ---- The answer -----------------------------------------------------------------------------------------------
class Answer(str):
    """An instant answer; `directions` gives each home's card a route link to the same store (by community name)."""
    directions = {}


def _rule(want):
    """'within a 15-minute walk of', 'at least a 10-minute drive of', 'within 1 mile on foot of'."""
    if want["metres"]:
        miles = f"{want['metres'] / 1609.34:.1f}".rstrip("0").rstrip(".")
        how = {"WALK": "on foot", "DRIVE": "by car", "TRANSIT": "by bus or train"}[want["mode"]]
        return f"{'at least' if want['at_least'] else 'within'} {miles} {'mile' if miles == '1' else 'miles'} {how} of"
    return f"{'at least' if want['at_least'] else 'within'} a {want['minutes']}-minute {MODE_WORD[want['mode']]} of"


def _rent(r, pool):
    if isinstance(r.get("monthly_rent"), (int, float)):
        per = "/person/installment" if r.get("rent_basis") == "per_person_installment" else "/person/month" if r.get("rental_space") == "room" else "/month"
        return f"from ${r['monthly_rent']:,.0f}{per}"
    est = rent_estimate(r, pool)
    return f"est. ${est['low']:,.0f}–${est['high']:,.0f}/month (estimate; ask the provider)" if est else "rent: ask the provider"


def _directions(home, store, mode):
    travel = {"WALK": "walking", "DRIVE": "driving", "TRANSIT": "transit"}[mode]
    url = (f"https://www.google.com/maps/dir/?api=1&origin={home['lat']},{home['lon']}"
           f"&destination={quote(store['name'] + (', ' + store['address'] if store['address'] else ''))}&travelmode={travel}")
    return url + (f"&destination_place_id={quote(store['place_id'])}" if store.get("place_id") else "")


def _line(t, stores, mode, pool, many):
    seconds, metres, j, h = t
    trip = f"{max(1, round(seconds / 60))} min {'walk' if mode == 'WALK' else 'drive' if mode == 'DRIVE' else 'by bus or train'}"
    trip += f" ({metres / 1609.34:.1f} mi)" if metres else ""
    to = f" to {stores[j]['name']}, {stores[j]['address'].split(',')[0]}" if many else ""
    kind = " (regular rental, not income-restricted)" if h.get("type") == "rental_listing" else ""
    phone = f" Call {h['phone']}." if h.get("phone") else ""
    return f"- **{h.get('community') or h['name']}**{kind}: {trip}{to}; {_rent(h, pool)}.{phone}"


def compose(found, want, result):
    """The instant answer text: the place and the limit first, then only homes whose measured trip fits."""
    stores, mode, rule = found["stores"], want["mode"], _rule(want)
    pool_all = filter_catalog(load_catalog(), {"types": ["affordable_listing", "rental_listing"]})  # for rent estimates
    many = len(stores) > 1
    it = "one of them" if many else "it"
    # The result comes first, naming the place; which store was picked (for a chain) follows it.
    place = found["label"] if not found.get("chain") else stores[0]["name"] + (f" ({stores[0]['address'].split(',')[0]})" if stores[0].get("address") else "")
    target = "one of these stores" if many else place
    lines = [found["label"] + "."]
    if result["routes"] is None:
        near = ", ".join(f"{h.get('community') or h['name']} ({min(nearby._miles(h['lat'], h['lon'], s['lat'], s['lon']) for s in stores):.1f} mi)" for h in result["nearest"])
        lines.append(f"Google Maps {ROUTE_WORD[mode]} routes didn't answer just now, so I can't say which homes are {rule} {it}. Please ask again in a minute.")
        if near:
            lines.append(f"Nearest verified homes in a straight line (not a {ROUTE_WORD[mode]} route, so not confirmed as close): {near}.")
        return Answer("\n".join(lines) + "\n\nThis is guidance, not legal advice.")
    matches = result["matches"]
    # "within a 15-minute walk of" -> "a 15-minute walk", for saying how the best options differ from what was asked.
    limit_words = rule.split(" of")[0].replace("within ", "").replace("at least ", "at least ")
    lines = [f"Here are verified homes {rule} {target}, measured with Google Maps {ROUTE_WORD[mode]} routes:" if matches
             else f"Here are the best options near {target}."]
    if found.get("chain") or many:
        lines.append(found["label"] + ".")
    shown = matches[:MAX_SHOWN]
    for t in shown:
        lines.append(_line(t, stores, mode, pool_all, many))
    if len(matches) > MAX_SHOWN:
        more = len(matches) - MAX_SHOWN
        lines.append(f"{more} more {'home also fits' if more == 1 else 'homes also fit'}; add a budget or a shorter time to narrow them.")
    alt = []
    if not matches:
        if result["over"]:
            cheap = bool(CHEAP.search(want["text"]))
            lines[0] = (f"Here are the best options near {target}: the {'lowest-priced' if cheap else 'closest'} ones, "
                        f"each a bit more than {limit_words} by Google Maps {ROUTE_WORD[mode]} routes.")
            alt = result["over"][:3]
        elif result.get("by_car"):
            lines[0] = f"Here are the closest homes to {target} by car; they're farther than an easy walk."
            alt = result["by_car"][:3]
        for t in alt:
            lines.append(_line(t, stores, "DRIVE" if t in result.get("by_car", []) else mode, pool_all, many))
        if not alt:
            lines[0] = (f"Here's how to keep looking near {target}: try a longer trip or a nearby town, "
                        "or call 211 for local housing help. Our list doesn't have a home close enough to measure yet.")
    missing = len(result["pool"]) - len(result["routes"])
    if missing:
        lines.append(f"Google found no {ROUTE_WORD[mode]} route for {missing} nearby home{'' if missing == 1 else 's'}, so {'it is' if missing == 1 else 'they are'} left out rather than guessed.")
    if mode == "WALK" and (matches or result["over"]):  # only when walking times are shown, not the by-car option
        lines.append("Walking times are Google's estimate at an average pace. They don't show sidewalks, crossings, steps or hills, so check the route if walking is hard.")
    if not want["stated"]:
        lines.append(_default_note(want))
    lines.append("Advertised rents and openings aren't guaranteed, so confirm with the property.\n\nThis is guidance, not legal advice.")
    answer = Answer("\n".join(lines))
    # Nothing within the limit: one-tap next searches, each backed by what was just measured.
    if not matches:
        what = "Rooms" if re.search(r"\brooms?\b", want["text"], re.I) else "Homes"
        follow = []
        if alt and not want["metres"] and not want["at_least"] and t_mode_ok(alt, result):
            longest = max(t[0] for t in alt) / 60
            follow.append(f"{what} within a {int(-(-longest // 5) * 5)}-minute {'walk' if mode == 'WALK' else 'drive' if mode == 'DRIVE' else 'bus ride'} of {target}")
        follow.append(f"Help paying rent near {target}")
        answer.suggest = follow
    answer.directions = {}
    for t in shown + alt:
        h = t[3]
        answer.directions[(h.get("community") or h["name"]).casefold()] = _directions(h, stores[t[2]], "DRIVE" if t in result.get("by_car", []) else mode)
    return answer


def t_mode_ok(alt, result):
    """The fallback list was measured in the asked mode (not the by-car stand-in), so a longer limit in that mode is real."""
    return not any(t in result.get("by_car", []) for t in alt)


def _default_note(want):
    """Said out loud whenever no time was given, since there's no universal "close"."""
    if want["mode"] == "WALK":
        return WALK_ASSUMED
    return f"I used up to {want['minutes']} minutes since no time was given. Want a different time? Just say so."


def _needs(want):
    """Requirements Gemma should weigh (pets, furnished...); a bus trip is the travel mode here, not a need."""
    return [n for n in requirements(want["text"]) if not (n == "transit" and want["mode"] == "TRANSIT")]


def answer(question, profile=None, history=None):
    """Instant answer (or one short question) for "something close to walmart"-style questions; None when it isn't one,
    or when other requirements (pets, furnished...) need Gemma, which then gets only the measured homes (for_gemma)."""
    want = read(question, history)
    if not want:
        return None
    found = resolve(want, profile, history)
    if "say" in found:
        return found["say"]
    if _needs(want):
        return None
    text = compose(found, want, measure(found, want, profile))
    if (profile or {}).get("accessible") is True:  # the find form's "accessible" box; homes aren't checked for it here
        text = with_directions(text.replace("\n\nThis is guidance", "\nYou need an accessible home: ask each property about step-free entry "
                                            "and the features you need, since this list doesn't check them.\n\nThis is guidance"), text.directions)
    return text


def progress(want):
    return f"Finding {'the ' + want['chain'] if want['chain'] else want['place']} and checking {ROUTE_WORD[want['mode']]} routes from verified homes…"


def for_gemma(want, history=None):
    """For a question Gemma answers: {"rows", "note", "directions"} with only the homes whose measured trip fits, or
    {"text"} when there's nothing for Gemma to weigh (a question to ask, no store found, no home close enough)."""
    found = resolve(want, None, history)
    if "say" in found:
        return {"text": found["say"]}
    result = measure(found, want, None)
    if result["routes"] is None or not result["matches"]:
        return {"text": compose(found, want, result)}
    stores = found["stores"]
    field = f"{'walk' if want['mode'] == 'WALK' else 'drive' if want['mode'] == 'DRIVE' else 'transit'}_minutes_to_{re.sub(r'[^a-z0-9]+', '_', (found['chain'] or stores[0]['name']).lower()).strip('_')}"
    rows, directions = [], {}
    for seconds, metres, j, h in result["matches"][:12]:
        row = dict(h)
        row[field] = f"{max(1, round(seconds / 60))} ({metres / 1609.34:.1f} mi, Google Maps route" + (f" to {stores[j]['address']})" if len(stores) > 1 else ")")
        rows.append(row)
        directions[(h.get("community") or h["name"]).casefold()] = _directions(h, stores[j], want["mode"])
    note = (f"Place: {found['label']}. Every listing below is {_rule(want)} {'one of these stores' if len(stores) > 1 else 'it'} by a Google Maps {ROUTE_WORD[want['mode']]} route "
            f"({field} is each home's minutes); homes farther away or without a route were already left out. Start with the place's name and address "
            "and that limit, give each home's time, and recommend only these listings. Route times don't show sidewalks, crossings, steps or hills; "
            "if walking is hard for them, say to check the route." + (f" Say this too: {_default_note(want)}" if not want["stated"] else ""))
    return {"rows": rows, "note": note, "directions": directions, "fallback": compose(found, want, result)}


def with_directions(text, directions):
    out = Answer(text)
    out.directions = directions or {}
    return out


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    t = time.time()
    print(answer(" ".join(sys.argv[1:])) or "(not a near-a-place question, or it needs Gemma)")
    print(f"\n[{time.time() - t:.1f}s]")
