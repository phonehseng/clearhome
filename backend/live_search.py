"""Let Gemma search the web for affordable listings in a Northern Virginia area, live.

Results are shown as "found on the web, not verified by our team". To keep them honest:
- Gemma uses Google Search grounding, and a result is kept only if its source is one of the
  pages Google actually returned for the search.
- Phone numbers are never taken from the web; people get the source link instead.
- Addresses are placed on the map only if the US Census Geocoder can match them.
- When running locally, new finds go to the review queue (data/candidates.json) for the team.

Usage: python backend/live_search.py "Woodbridge"
"""
import json
import re
import sys
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from google.genai import types

from catalog import load_catalog
from geocode import lookup
from matcher import MODEL, _get_client
from sources import CANDIDATES_PATH, _load_queue, _lock

CACHE_SECONDS = 6 * 3600
MAX_RESULTS = 6
REST_SECONDS = 20 * 60  # after Google Search fails (daily limit used up, or it drops the call), stop trying for a while
_cache, _cache_lock = {}, threading.Lock()
_resting_until = 0.0
RESTING = ("The web search isn't available right now (Google Search has reached its limit for today). "
           "The verified listings and the map still work.")


def area_for(location):
    """Map free text like 'Woodbridge' to a Northern Virginia jurisdiction, or None if outside it."""
    from advisor import area_for as shared
    return shared(location)


def _domain(url):
    host = urlsplit(url or "").hostname or ""
    return host[4:] if host.startswith("www.") else host


def _search(area, location):
    prompt = f"""You MUST use the Google Search tool before answering; do not answer from memory.
Search the web for apartments in {location} (in {area}, Virginia) that are CURRENTLY advertised
as affordable, income-restricted, low-income, tax-credit (LIHTC), workforce, or committed affordable housing.

Return ONLY a JSON array (no other text) of up to {MAX_RESULTS} objects with these keys:
"name", "address" (full street address if the page gives one, else null), "city",
"rent_text" (rent exactly as the page states, else null), "bedrooms_text" (else null),
"income_text" (the income limit or AMI percentage as stated, else null), "source_url" (the exact URL of the search-result page that lists this place, not just a home page).
Only include places that appear in your search results.
Only include places in {area}. Do not include phone numbers. Never guess a value; use null.
If you find nothing reliable, return []."""
    # One try with a hard limit, so the page never waits for minutes; the library's own retries are off. When it
    # fails (daily limit used up, or Google drops the call), searches rest for a while and answer at once instead.
    global _resting_until
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        http_options=types.HttpOptions(timeout=45_000, retry_options=types.HttpRetryOptions(attempts=1)))
    try:
        response = _get_client().models.generate_content(model=MODEL, contents=prompt, config=config)
    except Exception:
        _resting_until = time.time() + REST_SECONDS
        raise
    text = response.text or ""
    meta = response.candidates[0].grounding_metadata if response.candidates else None
    # Google lists the pages it returned; their titles are the sites' domains.
    seen = {(c.web.title or "").lower().removeprefix("www.") for c in (getattr(meta, "grounding_chunks", None) or []) if c.web}
    try:
        items = json.loads(re.search(r"\[.*\]", text, re.DOTALL).group(0))
    except Exception:
        return []
    results = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        url = str(item.get("source_url") or "")
        if not url.startswith("https://") or not _domain(url) or not any(_domain(url).endswith(d) or d.endswith(_domain(url)) for d in seen if d):
            continue  # not backed by a page Google actually returned
        results.append({k: (str(item[k])[:300] if item.get(k) is not None else None)
                        for k in ("name", "address", "city", "rent_text", "bedrooms_text", "income_text", "source_url")})
    return results[:MAX_RESULTS]


def _queue_for_review(area, results):
    """Add new finds to the review queue so the team can verify and publish them."""
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        queue = _load_queue()
        known = {r["id"] for r in queue["candidates"]} | set(queue["rejected"])
        for r in results:
            rid = "web-" + re.sub(r"[^a-z0-9]+", "-", f"{r['name']} {r.get('city') or ''}".lower()).strip("-")
            if rid in known:
                continue
            queue["candidates"].append({
                "id": rid, "name": r["name"], "type": "affordable_property", "origin": "gemma_web_search",
                "address": r.get("address"), "city": r.get("city"), "jurisdiction": area, "region": "New River Valley" if area == "Blacksburg" else "Northern Virginia", "state": "VA",
                "phone": None, "website": None, "cost": r.get("rent_text"), "who_it_serves": r.get("income_text"),
                "requirements": "Income limits apply; confirm with the property.", "accessible": None,
                "how_to_apply": "1. Open the source page and contact the property. 2. Ask about openings or the waitlist for affordable units.",
                "source_url": r["source_url"], "sources": [{"url": r["source_url"], "role": "provider"}],
                "lat": r.get("lat"), "lon": r.get("lon"), "data_as_of": now[:10], "verified": False, "last_verified": None,
                "verification_method": "Found by Gemma web search; not yet reviewed by the team.",
                "notes": "Found automatically on the web. Check the source page before approving."})
            known.add(rid)
        CANDIDATES_PATH.write_text(json.dumps(queue, indent=2) + "\n")


def search(location, queue_results=True):
    """Returns {"area": ..., "results": [...]} or {"error": ...}."""
    area = area_for(location)
    if not area:
        return {"error": "Clear Home covers Northern Virginia and Blacksburg, VA. Try Blacksburg, Arlington, or Woodbridge."}
    key = " ".join(location.lower().split())
    with _cache_lock:
        hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    if time.time() < _resting_until:
        return {"error": RESTING}
    reviewed = {str(r.get("community") or r.get("name")).casefold() for r in load_catalog()}
    try:
        found = _search(area, location)
    except Exception:
        return {"error": RESTING}
    results = [r for r in found if r["name"].casefold() not in reviewed]
    for r in results:
        point = None
        if r.get("address") and re.match(r"\s*\d", r["address"]):
            try:
                point = lookup(r["address"])
            except Exception:
                point = None
        r["lat"], r["lon"] = point if point else (None, None)
    if queue_results and results:
        _queue_for_review(area, results)
    out = {"area": area, "results": results,
           "notice": "Found on the web by AI just now. Not verified by our team: confirm rent, eligibility and availability with the property."}
    with _cache_lock:
        _cache[key] = (time.time(), out)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(json.dumps(search(" ".join(sys.argv[1:]), queue_results=False), indent=2))
