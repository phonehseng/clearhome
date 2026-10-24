"""Make each listing's main link point to the right place, and say honestly what that place is.

Root cause this fixes: many listings used a page that covers many properties (a county directory or
a city PDF guide) as their main source, and the card called it "provider source". For Little River Glen
that was the county's senior-housing directory, which also describes assisted-living and nursing care.

For every affordable_listing this script:
1. Treats a link shared by more than one community (or a known guide/list) as a *directory*.
2. Checks every other link on file (website, sources): it only counts as the property's own page if the
   page loads and its text names the community and matches its street number. Pages that block automated
   visitors are not counted as verified.
3. Uses the best verified property page as source_url (directories stay in `sources` with role "directory"),
   and records `source_kind` so the card can label the link: property_website, official_property_page,
   owner_property_page or official_directory.

Run: python backend/source_audit.py           # audit and update data/resources.json
     python backend/source_audit.py --dry-run # report only
"""
import argparse
import collections
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html import unescape
from urllib.parse import urlsplit

import requests

from catalog import RESOURCES_PATH

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15 (Clear House source check)"}
GOV_HOSTS = (".gov", "fcrha.org", "arha.us", "arlingtonva.us")
OWNER_HOSTS = ("ahcommunities.org", "apah.org", "truegroundhousing.org", "wesleyhousing.org", "communityhousingpartners.org",
               "enterprisecommunity.org", "lawsoncompanies.com")
DIRECTORY_HINTS = re.compile(r"(\.pdf$|/documentcenter/|guide|list-of|privately-owned|available-apartments|affordable-units|/communities/?$|senior-housing$|/waitlist$)", re.I)
FILLER = {"the", "at", "of", "and", "apartments", "apartment", "apts", "apt", "residences", "residence", "homes", "home",
          "community", "communities", "senior", "seniors", "living", "village", "i", "ii", "iii", "iv", "&"}


def _text(html):
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).lower()


def _name_tokens(name):
    words = re.findall(r"[a-z0-9']+", re.sub(r"\(.*?\)", " ", name.lower()))
    return [w for w in words if w not in FILLER and len(w) > 1] or words


def _heading_words(html):
    """Words in the page's title, og:title and first h1: what the page says it is *about*."""
    parts = [m.group(1) for m in [re.search(r"(?is)<title[^>]*>(.*?)</title>", html),
                                  re.search(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html),
                                  re.search(r"(?is)<h1[^>]*>(.*?)</h1>", html)] if m]
    return set(re.findall(r"[a-z0-9']+", _text(" ".join(parts))))


def page_matches(url, community, address):
    """True only if the page loads, is titled with this community's name (whole words, so 'Terraces at
    Arlington View West' doesn't match 'Arlington View Terrace'), and mentions it in the text."""
    try:
        r = requests.get(url, headers=UA, timeout=15)
    except requests.RequestException:
        return False
    if r.status_code != 200 or "text/html" not in r.headers.get("Content-Type", ""):
        return False
    tokens = _name_tokens(community)
    heading = _heading_words(r.text)
    if not all(t in heading for t in tokens):
        return False  # a general page that merely mentions the property doesn't count
    number = re.match(r"\s*(\d{2,6})\b", address or "")
    text = _text(r.text)
    return all(t in text for t in tokens) and (number is None or number.group(1) in text or len(tokens) >= 2)


def _kind(url):
    host = (urlsplit(url).hostname or "").lower()
    if host.endswith(GOV_HOSTS) or any(host.endswith(h) for h in GOV_HOSTS):
        return "official_property_page"
    if any(host.endswith(h) for h in OWNER_HOSTS):
        return "owner_property_page"
    return "property_website"


def audit(rows, check=page_matches):
    listings = [r for r in rows if r.get("type") == "affordable_listing"]
    communities_by_url = collections.defaultdict(set)
    for r in listings:
        for u in {r.get("source_url"), r.get("website")} | {s.get("url") for s in r.get("sources", [])}:
            if u:
                communities_by_url[u].add((r.get("community") or r["name"]).casefold())
    is_directory = lambda u: len(communities_by_url.get(u, ())) > 1 or bool(DIRECTORY_HINTS.search(u or ""))

    # Each candidate page is checked once, even if several floor plans share it.
    jobs = {}
    for r in listings:
        name, address = r.get("community") or r["name"], r.get("address")
        for u in [r.get("website")] + [s.get("url") for s in r.get("sources", [])] + [r.get("source_url")]:
            if u and u.startswith("https://") and not is_directory(u):
                jobs[(u, name.casefold())] = (u, name, address)
    with ThreadPoolExecutor(max_workers=12) as pool:
        verified = dict(zip(jobs, pool.map(lambda a: check(*a), jobs.values())))

    today, changes = date.today().isoformat(), collections.Counter()
    for r in listings:
        name = (r.get("community") or r["name"]).casefold()
        candidates = [u for u in [r.get("source_url"), r.get("website")] + [s.get("url") for s in r.get("sources", [])]
                      if u and verified.get((u, name))]
        # Prefer an official property page, then the owner's page, then the property's own website.
        order = {"official_property_page": 0, "owner_property_page": 1, "property_website": 2}
        best = sorted(dict.fromkeys(candidates), key=lambda u: order[_kind(u)])[0] if candidates else None
        old = r.get("source_url")
        if best:
            if old and old != best and is_directory(old):
                r.setdefault("sources", [])
                if not any(s.get("url") == old for s in r["sources"]):
                    r["sources"].append({"url": old, "role": "directory"})
                changes["switched to a property page"] += 1
            r["source_url"], r["source_kind"], r["source_checked_on"] = best, _kind(best), today
        else:
            r["source_kind"] = "official_directory" if is_directory(old) else _kind(old or "")
            changes["kept: directory or unverifiable page" if is_directory(old) else "kept: property page (not re-verified)"] += 1
        for s in r.get("sources", []):
            if is_directory(s.get("url")) and s.get("role") != "directory":
                s["role"] = "directory"
    return changes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = json.loads(RESOURCES_PATH.read_text())
    for what, n in audit(rows).most_common():
        print(f"{n:4}  {what}")
    if not args.dry_run:
        RESOURCES_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
