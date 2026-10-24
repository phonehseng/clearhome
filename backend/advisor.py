"""Answer questions about low-income housing in Northern Virginia, grounded in the verified catalog.

Usage: python backend/advisor.py "How do I qualify for a housing voucher in Arlington?"
"""
import json
import re
import sys
import threading
import time

from catalog import filter_catalog, load_catalog, serves_location
from matcher import ask_gemma

# Fields Gemma needs to answer; the rest (photos, internal review data) only adds tokens.
FIELDS = ("id", "name", "type", "jurisdiction", "city", "address", "phone", "website", "hours", "who_it_serves",
          "cost", "monthly_rent", "bedrooms", "minimum_age", "requirements", "how_to_apply", "waitlist_status",
          "source_url", "last_verified", "region", "service_areas", "rental_space", "price_unit", "rent_basis",
          "lease_type", "lease_responsibility", "lease_start", "lease_end", "payment_schedule", "shared_home_bedrooms")


# Gemma's free tier allows about 16,000 input tokens a minute, so each question only sends
# the records it's about, with long fields trimmed.
MAX_RECORDS = 18
MAX_FIELD = 350
AREAS = [  # longest names first, so "manassas park" wins over "manassas"
    ("blacksburg", "Blacksburg"), ("virginia tech", "Blacksburg"),
    ("manassas park", "Manassas Park City"), ("manassas", "Manassas City"), ("falls church", "Falls Church City"),
    ("fairfax city", "Fairfax City"), ("city of fairfax", "Fairfax City"), ("fairfax station", "Fairfax County"),
    ("fairfax county", "Fairfax County"), ("fairfax", "Fairfax County"),
    ("reston", "Fairfax County"), ("herndon", "Fairfax County"), ("mclean", "Fairfax County"), ("vienna", "Fairfax County"),
    ("tysons", "Fairfax County"), ("springfield", "Fairfax County"), ("annandale", "Fairfax County"), ("burke", "Fairfax County"),
    ("centreville", "Fairfax County"), ("chantilly", "Fairfax County"), ("lorton", "Fairfax County"), ("oakton", "Fairfax County"),
    ("great falls", "Fairfax County"), ("mount vernon", "Fairfax County"), ("franconia", "Fairfax County"), ("merrifield", "Fairfax County"),
    ("arlington", "Arlington County"), ("ballston", "Arlington County"), ("clarendon", "Arlington County"), ("crystal city", "Arlington County"),
    ("rosslyn", "Arlington County"), ("columbia pike", "Arlington County"),
    ("alexandria", "Alexandria City"), ("old town", "Alexandria City"), ("del ray", "Alexandria City"),
    ("loudoun", "Loudoun County"), ("leesburg", "Loudoun County"), ("sterling", "Loudoun County"), ("ashburn", "Loudoun County"),
    ("purcellville", "Loudoun County"), ("south riding", "Loudoun County"), ("brambleton", "Loudoun County"),
    ("prince william", "Prince William County"), ("woodbridge", "Prince William County"), ("dumfries", "Prince William County"),
    ("gainesville", "Prince William County"), ("haymarket", "Prince William County"), ("bristow", "Prince William County"),
    ("dale city", "Prince William County"), ("lake ridge", "Prince William County"), ("triangle", "Prince William County"),
    ("montclair", "Prince William County"),
]
TOPICS = [
    (("voucher", "section 8", "hcv", "public housing", "waitlist", "wait list", "housing authority", "qualify", "eligib", "income"), {"housing_authority"}),
    (("rent help", "behind on rent", "evict", "late", "can't pay", "cant pay", "assistance", "deposit", "utility"), {"rental_assistance", "legal_aid"}),
    (("lawyer", "legal", "landlord", "rights", "repair", "court"), {"legal_aid"}),
    (("apartment", "listing", "unit", "bedroom", "studio", "affordable", "move", "rent is", "qualify", "income"), {"affordable_listing"}),
    (("shelter", "tonight", "homeless", "street", "nowhere", "sleep"), {"emergency_shelter", "other"}),
    (("senior", "elderly", "55", "62"), {"affordable_listing", "housing_authority"}),
]


def _pick(resources, question):
    q = question.lower()
    areas = set()
    for word, area in AREAS:
        if word in q and not any(word in longer and longer in q for longer, _ in AREAS if longer != word and word in longer):
            areas.add(area)
    types = set().union(*[t for words, t in TOPICS if any(w in q for w in words)]) or {"housing_authority", "rental_assistance", "affordable_listing"}
    def serves(r):  # "area" covers programs shared across places, like Prince William's intake line
        return any(serves_location(r, area) for area in areas or {'Northern Virginia'})

    picked = [r for r in resources if r.get("type") in types and serves(r)]
    # Local records before region-wide ones, so the cap keeps what's most relevant.
    picked.sort(key=lambda r: r.get("jurisdiction") == "Northern Virginia")
    return picked[:MAX_RECORDS]


def _compact(row):
    out = {k: (row[k][:MAX_FIELD] if isinstance(row[k], str) else row[k]) for k in FIELDS if row.get(k) not in (None, "")}
    if isinstance(row.get("availability"), dict):
        out["availability_status"] = row["availability"].get("status")
        out["availability_checked_on"] = row["availability"].get("checked_on")
    return out


# Gemma 4 always "thinks" before answering, so a reply takes 20-60 seconds on the free tier.
# Repeated questions (like the example buttons) are answered from this cache instead.
CACHE_SECONDS = 12 * 3600
_cache, _cache_lock = {}, threading.Lock()


def ask(question, history=None):
    key = " ".join(question.lower().split())
    if not history:
        with _cache_lock:
            hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_SECONDS:
            return hit[1]
    answer = _ask(question, history)
    if not history:
        with _cache_lock:
            _cache[key] = (time.time(), answer)
    return answer


# The example buttons on the resources page; keep in sync with frontend/resources.html.
EXAMPLES = ['How do I qualify for Section 8?', 'Which voucher waitlists are open right now?', "I'm behind on rent in Alexandria. Who can help?", 'What documents do I need to apply?', 'Affordable 1-bedroom apartments in Arlington?']


def warm_examples(gap_seconds=25):
    """Answer the example questions in the background so the buttons reply instantly.
    Spaced out to stay under the free tier's per-minute token limit."""
    def run():
        for question in EXAMPLES:
            try:
                ask(question)
            except Exception:
                pass  # a failed warm-up just means that button waits for Gemma
            time.sleep(gap_seconds)
    threading.Thread(target=run, daemon=True).start()


def _ask(question, history=None):
    # filter_catalog drops closed and overdue listings; _pick keeps the prompt small.
    resources = [_compact(r) for r in _pick(filter_catalog(load_catalog()), " ".join([question] + [t['text'] for t in (history or [])[-2:]]))]
    past = "\n".join(f"{turn['role']}: {turn['text']}" for turn in (history or [])[-4:])
    prompt = f"""You are a patient, plain-spoken housing advisor for people in Northern Virginia and Blacksburg, Virginia.
Blacksburg includes student rooms near Virginia Tech. Northern Virginia and Blacksburg are separate service regions.

Rules:
- For anything local (program names, phone numbers, addresses, websites, rents, waitlist status, deadlines), use ONLY the resources below. Never invent them.
- You may explain widely known federal basics (for example: Housing Choice Vouchers usually require income at or below 50% of area median income, and tenants usually pay about 30% of income toward rent; tax-credit apartments usually cap income at 50-60% of area median income). Say these are general rules and the program sets the final limits.
- State waitlist_status exactly. Never say a waitlist is open unless waitlist_status is "open". If the waitlists the person needs are closed, say so kindly and point to programs that can still help (rent assistance, legal aid, 211).
- availability_status for listings is a website snapshot, not a guaranteed vacancy.
- A room price is per person, not the price of the entire shared home. State the payment schedule, lease dates, and individual versus joint responsibility exactly as recorded. Do not divide a whole-apartment price and present it as an advertised room.
- When you recommend a resource, give its name, phone and how to apply, and mention its source_url.
- Typical documents to prepare: photo ID, Social Security numbers or immigration documents for household members, proof of income (pay stubs, benefit letters), and your current lease or eviction notice. Say the program decides the final list.
- If the person may be unsafe or without shelter tonight, start with: call 911 in an emergency, or 211 for shelter.
- Never ask for or repeat SSNs, bank details or other sensitive data.
- Keep it short and plain: a direct answer first, then up to 5 bullet points. Use **bold** only for names. End with one line saying this is guidance, not legal advice.
- If the question is not about housing, gently steer back to housing help.

Earlier in this conversation:
{past or "(none)"}

Question: {question}

Resources (source-reviewed, for the requested area):
{json.dumps(resources, ensure_ascii=False)}"""
    return ask_gemma(prompt)


def programs():
    """Verified non-shelter help (vouchers, rent help, legal aid, other services) for the resources page."""
    keep = {"housing_authority", "rental_assistance", "legal_aid", "other"}
    return [_compact(r) for r in load_catalog() if r.get("type") in keep and not isinstance(r.get("availability"), dict)]


# Common places people mention that are outside Clear House's service area.
OUTSIDE = r"\b(richmond|baltimore|maryland|silver spring|bethesda|rockville|washington,? dc|d\.?c\.?|norfolk|virginia beach|chesapeake|charlottesville|roanoke|fredericksburg|stafford|winchester|harrisonburg|lynchburg|frederick)\b"


# Well-known places people ask to live near: (area, approximate latitude, longitude).
LANDMARKS = {
    "george mason": ("Fairfax County", 38.8297, -77.3074), "gmu": ("Fairfax County", 38.8297, -77.3074),
    "virginia tech": ("Blacksburg", 37.2284, -80.4234), "vt campus": ("Blacksburg", 37.2284, -80.4234),
    "nova community college": ("Fairfax County", 38.8325, -77.2365), "nvcc": ("Fairfax County", 38.8325, -77.2365),
    "marymount": ("Arlington County", 38.8968, -77.1270), "pentagon": ("Arlington County", 38.8719, -77.0563),
}


def area_for(text):
    """Resolve Northern Virginia places or Blacksburg; general requests default to NoVA."""
    t = (text or "").lower()
    landmark = next((v[0] for k, v in LANDMARKS.items() if re.search(rf"\b{re.escape(k)}\b", t)), None)
    if landmark:
        return landmark
    area = next((area for word, area in AREAS if word in t), None)
    if area:
        return area
    if re.search(OUTSIDE, t):
        return None
    if not t.strip() or "northern virginia" in t or t.strip() in ("nova", "northern va"):
        return "Northern Virginia"
    # A specific place we don't recognize is treated as outside; general requests cover the whole region.
    return "Northern Virginia" if len(t.split()) > 2 else None


# About 60% of area median income in Northern Virginia, from the limits Fairfax County publishes for its
# affordable senior housing ($68,880 for 1 person, $78,720 for 2), scaled with HUD's standard household-size
# factors. Programs set their own exact limits; this only decides whether to show assistance programs.
_MEDIAN_60 = 98_400  # 60% of median for a 4-person household
_SIZE_FACTOR = {1: 0.7, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.08, 6: 1.16}


def assistance_income_limit(household):
    """About 80% of area median income for this household size: the usual ceiling for assistance programs."""
    size = household if isinstance(household, int) and household > 0 else 1
    factor = _SIZE_FACTOR.get(size, 1.16 + 0.08 * (size - 6))
    return round(_MEDIAN_60 * factor * 80 / 60, -2)


def program_need(profile):
    """Whether to show rent help, vouchers and legal aid, plus a short note when income rules them out."""
    from prompt_tools import keyword_filters  # imported here: prompt_tools imports this module
    # The NoVA screening estimate is not a Blacksburg income limit. Local
    # agencies must assess eligibility; retain their contacts without a cutoff.
    if area_for(profile.get('location')) == 'Blacksburg':
        return True, None
    if profile.get("tonight") or profile.get("voucher"):
        return True, None
    text_types = set(keyword_filters(profile.get("situation") or "")[0]["types"]) & {"rental_assistance", "housing_authority", "legal_aid", "emergency_shelter"}
    if text_types or re.search(r"\b(low[- ]income|afford|struggl|section 8|voucher|evict|behind)\b", (profile.get("situation") or "").lower()):
        return True, None
    income = profile.get("income")
    if isinstance(income, (int, float)) and income > 0:
        limit = assistance_income_limit(profile.get("household"))
        if income <= limit:
            return True, None
        return False, (f"With a household income of ${income:,.0f}, most rent-help and voucher programs likely don't apply "
                       f"(they usually stop around ${limit:,.0f} for your household size). Some listings have higher income tiers.")
    return False, None


def options(profile):
    """Instant, no-AI matches for the find form: listings, programs and (if urgent) shelters for an area."""
    area = area_for(profile.get("location"))
    if area is None:
        return {"error": "Clear House covers Northern Virginia and Blacksburg, VA. Try Blacksburg, Reston, or Woodbridge."}
    base = {"locations": [area], "needs_accessible": bool(profile.get("accessible"))}
    listing_filters = {**base, "types": ["affordable_listing", "rental_listing"],
                       "age_group": "all" if profile.get("senior") else "general"}
    if profile.get('rental_space') in {'room', 'entire_home'}:
        listing_filters['rental_space'] = profile['rental_space']
    if profile.get("budget"):
        listing_filters["max_budget_per_month"] = profile["budget"]
    if profile.get("bedrooms") is not None:
        listing_filters["bedrooms"] = profile["bedrooms"]
    listing_filters["age"] = 62 if profile.get("senior") else 30  # 30 excludes senior-only homes for younger people
    if profile.get("tonight"):
        listing_filters["urgency"] = "emergency"
    rows = load_catalog()
    keep = lambda r: {**_compact(r), "lat": r.get("lat"), "lon": r.get("lon"), "floor_plan": r.get("floor_plan"), "community": r.get("community")}
    listings = [keep(r) for r in filter_catalog(rows, listing_filters)]
    listings.sort(key=lambda r: (area == 'Blacksburg' and r.get('rental_space') != 'room',
                                 r.get('monthly_rent') if isinstance(r.get('monthly_rent'), (int, float)) else float('inf')))
    listings = listings[:12]
    programs = [keep(r) for r in filter_catalog(rows, {**base, "needs_accessible": False, "types": ["housing_authority", "rental_assistance", "legal_aid"]})
                if not isinstance(r.get("availability"), dict)][:12]
    shelters = [keep(r) for r in filter_catalog(rows, {**base, "needs_accessible": False, "types": ["emergency_shelter", "other"], "urgency": "emergency"})
                if r["type"] == "emergency_shelter" or "intake" in str(r.get("name", "")).lower() or "coordinated" in str(r.get("name", "")).lower()][:10] if profile.get("tonight") else []
    need, income_note = program_need(profile)
    return {"area": area, "listings": listings, "programs": programs, "shelters": shelters,
            "programs_relevant": need, "income_note": income_note}


NEAR = re.compile(r"\b(near|close to|by|around|next to|walking distance|walk to|within \d+ (?:mi|miles?))\b")


def quick_nearby(question, profile=None):
    """Answer "one near George Mason"-style questions straight from the catalog, with no AI call.
    Returns None when the question isn't a simple "near a place" request."""
    import math
    q = (question or "").lower()
    if not NEAR.search(q):
        return None
    landmark = next(((k, v) for k, v in LANDMARKS.items() if re.search(rf"\b{re.escape(k)}\b", q)), None)
    area = landmark[1][0] if landmark else area_for(question)
    if not area or area == "Northern Virginia":
        return None
    profile = profile or {}
    # Regular rentals (e.g. Blacksburg student rooms) are included but labeled, so they're never mistaken for subsidized housing.
    filters = {"types": ["affordable_listing", "rental_listing"], "locations": [area], "age": 62 if profile.get("senior") else 30}
    if isinstance(profile.get("budget"), (int, float)) and profile["budget"] > 0:
        filters["max_budget_per_month"] = profile["budget"]
    rows = filter_catalog(load_catalog(), filters)
    seen, homes = set(), []
    for r in rows:
        key = (r.get("community") or r["name"]).casefold()
        if key not in seen:
            seen.add(key)
            homes.append(r)
    if landmark:
        _, (_, lat, lon) = landmark
        def miles(r):
            if r.get("lat") is None:
                return None
            dlat, dlon = math.radians(r["lat"] - lat), math.radians(r["lon"] - lon)
            h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(r["lat"])) * math.sin(dlon / 2) ** 2
            return 3958.8 * 2 * math.asin(math.sqrt(h))
        homes.sort(key=lambda r: (miles(r) is None, miles(r) or 0))
    place = landmark[0].title().replace("Gmu", "George Mason University") if landmark else area
    if not homes:
        return (f"I don't have a reviewed home in {area} that fits your choices yet. Try a higher budget or a nearby area, "
                "or call 211 for local housing help.\n\nThis is guidance, not legal advice.")
    lines = [f"Here are reviewed homes closest to {place}:" if landmark else f"Here are reviewed homes in {area}:"]
    for r in homes[:5]:
        rent = f"from ${r['monthly_rent']:,.0f}/month" if isinstance(r.get("monthly_rent"), (int, float)) else "rent: ask the provider"
        dist = ""
        if landmark and r.get("lat") is not None:
            dist = f", about {miles(r):.1f} mi away (straight line)"
        phone = f" Call {r['phone']}." if r.get("phone") else ""
        kind = " (regular rental, not income-restricted)" if r.get("type") == "rental_listing" else ""
        lines.append(f"- **{r.get('community') or r['name']}**{kind}: {rent}{dist}.{phone}")
    lines.append("Advertised rents and openings aren't guaranteed, so confirm with the property. "
                 "For real walking times, use \"Live near a…\" under More options.\n\nThis is guidance, not legal advice.")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(ask(" ".join(sys.argv[1:])))
