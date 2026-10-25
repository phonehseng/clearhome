"""Hotels and motels near a place, for someone who needs somewhere to stay tonight.

No AI is involved. Google Places Text Search finds budget hotels and motels in or near the area; when Google knows a
price level, cheaper ones come first (Google's own order otherwise). These places aren't verified by our team, so the page labels them as
Google Maps results and says to call for tonight's rate. Each gets an estimated nightly range (see estimate), shown as an
estimate along with what it's based on. Without a Maps key (or if Google doesn't answer), the list
is empty and the page still gets a Google Maps search link.

Usage: python backend/hotels.py "Arlington"
"""
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from advisor import area_for
from nearby import PLACES_TEXT_URL, REGIONS, _key, _miles, _post

MAX_HOTELS = 6
CACHE_SECONDS = 6 * 3600
# Places that rent a room by the night. Resorts, B&Bs, campgrounds and RV parks are left out.
ROOM_TYPES = {"hotel", "motel", "extended_stay_hotel", "inn", "hostel", "lodging"}
PRICE = {"PRICE_LEVEL_FREE": (0, "Free"), "PRICE_LEVEL_INEXPENSIVE": (1, "$ · Inexpensive"), "PRICE_LEVEL_MODERATE": (2, "$$ · Moderate"),
         "PRICE_LEVEL_EXPENSIVE": (3, "$$$ · Expensive"), "PRICE_LEVEL_VERY_EXPENSIVE": (4, "$$$$ · Very expensive")}
UNKNOWN_PRICE = 2.5  # no price level from Google: after the inexpensive and moderate ones, before the expensive ones
# What a night usually costs, so someone can tell a $70 motel from a $200 hotel before calling. Google rarely gives hotels
# a price, so this is an estimate, never a quote: by Google's price level when it has one, else by the brand's chain scale,
# else (an independent) the economy range. Typical weeknight rates; Northern Virginia runs higher than Blacksburg.
NIGHTLY = {"Northern Virginia": {"economy": (75, 120), "midscale": (105, 160), "upper midscale": (140, 220), "upscale": (190, 320), "luxury": (300, 500)},
           "Blacksburg": {"economy": (60, 95), "midscale": (80, 130), "upper midscale": (110, 175), "upscale": (150, 250), "luxury": (220, 380)}}
LEVEL_TIER = {"PRICE_LEVEL_INEXPENSIVE": ("economy", "Inexpensive"), "PRICE_LEVEL_MODERATE": ("midscale", "Moderate"),
              "PRICE_LEVEL_EXPENSIVE": ("upscale", "Expensive"), "PRICE_LEVEL_VERY_EXPENSIVE": ("luxury", "Very expensive")}
# Checked in this order, so "Hampton Inn by Hilton" is upper midscale before "Hilton" can make it upscale,
# and "Days Inn by Wyndham" is economy before "Wyndham" does.
BRANDS = [(tier, re.compile(rf"\b(?:{names})\b", re.I)) for tier, names in (
    ("economy", r"motel 6|studio 6|super 8|days inn|econo lodge|red roof|rodeway|travelodge|budget inn|red carpet inn|surestay|howard johnson|"
                r"knights inn|america.?s best value|extended stay america|woodspring|intown suites"),
    ("midscale", r"quality inn|comfort (?:inn|suites)|sleep inn|la quinta|baymont|wingate|microtel|country inn|best western|candlewood|ramada|clarion"),
    ("upper midscale", r"hampton inn|hilton garden inn|courtyard|fairfield inn|holiday inn|homewood|residence inn|springhill|towneplace|hyatt place|home2|tru"),
    ("upscale", r"marriott|hilton|hyatt|sheraton|westin|embassy suites|doubletree|crowne plaza|renaissance|radisson|wyndham|staybridge|kimpton|aloft"))]
FIELDS = ("places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.priceLevel,"
          "places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.businessStatus,places.primaryType,places.primaryTypeDisplayName")
# A chat question is about a room for tonight (the person's own words, not the form's checkboxes).
NEEDS_A_ROOM = re.compile(r"\b(tonight|place to (?:stay|sleep)|somewhere (?:safe )?to (?:stay|sleep)|nowhere to (?:go|sleep|stay)|homeless|"
                          r"on the street|sleep(?:ing)? in (?:my|a) car|kicked out|evicted today|shelters?|hotels?|motels?)\b", re.I)
_cache, _lock = {}, threading.Lock()
_pool = ThreadPoolExecutor(max_workers=4)


def _label(place, area):
    """How the place is named to Google: what the person typed, with ", VA" so Arlington isn't Arlington, Texas."""
    label = (place or "").strip() or area
    return label if re.search(r"\b(va|virginia)\b", label, re.I) else f"{label}, VA"


def search_url(label):
    return "https://www.google.com/maps/search/?api=1&query=" + quote(f"hotels near {label}")


def near(place):
    """{"area", "place", "hotels", "search_url"} for a place in Northern Virginia or Blacksburg, or None outside them."""
    area = area_for(place)
    if area is None:
        return None
    label = _label(place, area)
    return {"area": area, "place": label, "hotels": _lookup(label, area), "search_url": search_url(label)}


def estimate(name, level, area):
    """{"low", "high", "basis"}: what a night likely costs here, and what that guess rests on (shown with it)."""
    region = "Blacksburg" if area == "Blacksburg" else "Northern Virginia"
    if level in LEVEL_TIER:
        tier, word = LEVEL_TIER[level]
        basis = f"Google lists it as {word}; typical {region} rate"
    else:
        tier, brand = next(((t, m.group(0)) for t, pattern in BRANDS if (m := pattern.search(name or ""))), ("economy", None))
        basis = (f"{brand} is {'an' if tier[0] in 'aeiou' else 'a'} {tier.replace(' ', '-')} chain; typical {region} rate" if brand
                 else f"Not a chain we know; typical {region} economy rate")
    low, high = NIGHTLY[region][tier]
    return {"low": low, "high": high, "basis": basis}


def _lookup(label, area):
    if not _key():
        return []
    key = label.lower()
    with _lock:
        hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    region = REGIONS[1] if area == "Blacksburg" else REGIONS[0]
    try:
        # "budget" matters: without it Google leads with airport and business hotels.
        data = _post(PLACES_TEXT_URL, {"textQuery": f"budget hotels and motels near {label}", "includedType": "lodging", "maxResultCount": 15,
                                       "locationBias": {"circle": {"center": {"latitude": region[1], "longitude": region[2]}, "radius": 50000.0}}},
                     FIELDS)
    except Exception:
        return []  # not cached, so the next person gets a fresh try
    hotels = []
    for p in data.get("places", []):
        where = p.get("location") or {}
        if (p.get("businessStatus") not in (None, "OPERATIONAL") or p.get("primaryType") not in ROOM_TYPES
                or "latitude" not in where or _miles(where["latitude"], where["longitude"], region[1], region[2]) > region[3]):
            continue
        rank, price = PRICE.get(p.get("priceLevel"), (UNKNOWN_PRICE, None))
        name = (p.get("displayName") or {}).get("text")
        hotels.append({k: v for k, v in {
            "name": name, "kind": (p.get("primaryTypeDisplayName") or {}).get("text"),
            "address": p.get("formattedAddress"), "phone": p.get("nationalPhoneNumber"),
            "website": p.get("websiteUri") if str(p.get("websiteUri", "")).startswith("https://") else None,
            "maps_url": p.get("googleMapsUri"), "rating": p.get("rating"), "ratings": p.get("userRatingCount"), "price": price,
            "estimate": estimate(name, p.get("priceLevel"), area), "lat": where["latitude"], "lon": where["longitude"], "_rank": rank,
        }.items() if v not in (None, "")})
    hotels = sorted((h for h in hotels if h.get("name")), key=lambda h: h["_rank"])[:MAX_HOTELS]  # stable: Google's order stays within a level
    for h in hotels:
        del h["_rank"]
    with _lock:
        if len(_cache) > 200:  # keyed on user text, so keep it bounded
            _cache.clear()
        _cache[key] = (time.time(), hotels)
    return hotels


def place_for(question, profile=None):
    """Where to look for hotels when a chat question asks for somewhere to stay tonight, else None."""
    if not NEEDS_A_ROOM.search(question or ""):
        return None
    # A place named in the question wins ("tonight in Arlington"); otherwise the find form's location.
    # area_for falls back to "Northern Virginia" for any longer sentence, so that only counts when they said it.
    named = area_for(question)
    if named and (named != "Northern Virginia" or re.search(r"northern virginia|\bnova\b", question, re.I)):
        return named
    location = (profile or {}).get("location")
    location = location.strip()[:100] if isinstance(location, str) else ""
    return location if location and area_for(location) else named


def lookup_later(place):
    """Start the lookup now (it runs while Gemma writes) and collect it with .result()."""
    return _pool.submit(near, place)


if __name__ == "__main__":
    print(json.dumps(near(" ".join(sys.argv[1:]) or "Northern Virginia"), indent=2))
