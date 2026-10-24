"""Answer questions about low-income housing in Northern Virginia, grounded in the verified catalog.

Usage: python backend/advisor.py "How do I qualify for a housing voucher in Arlington?"
"""
import json
import sys
import threading
import time

from catalog import filter_catalog, load_catalog
from matcher import ask_gemma

# Fields Gemma needs to answer; the rest (photos, internal review data) only adds tokens.
FIELDS = ("id", "name", "type", "jurisdiction", "city", "address", "phone", "website", "hours", "who_it_serves",
          "cost", "monthly_rent", "bedrooms", "minimum_age", "requirements", "how_to_apply", "waitlist_status",
          "source_url", "last_verified")


# Gemma's free tier allows about 16,000 input tokens a minute, so each question only sends
# the records it's about, with long fields trimmed.
MAX_RECORDS = 18
MAX_FIELD = 350
AREAS = [  # longest names first, so "manassas park" wins over "manassas"
    ("manassas park", "Manassas Park City"), ("manassas", "Manassas City"), ("falls church", "Falls Church City"),
    ("fairfax city", "Fairfax City"), ("city of fairfax", "Fairfax City"), ("fairfax", "Fairfax County"),
    ("arlington", "Arlington County"), ("alexandria", "Alexandria City"),
    ("loudoun", "Loudoun County"), ("leesburg", "Loudoun County"), ("sterling", "Loudoun County"), ("ashburn", "Loudoun County"),
    ("prince william", "Prince William County"), ("woodbridge", "Prince William County"), ("dumfries", "Prince William County"),
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
        where = f"{r.get('jurisdiction')} {r.get('area') or ''}"
        return not areas or r.get("jurisdiction") == "Northern Virginia" or any(a in where for a in areas)

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
    prompt = f"""You are a patient, plain-spoken housing advisor for low-income people in Northern Virginia
(Fairfax County, Fairfax City, Falls Church, Arlington, Alexandria, Loudoun, Prince William, Manassas, Manassas Park).

Rules:
- For anything local (program names, phone numbers, addresses, websites, rents, waitlist status, deadlines), use ONLY the resources below. Never invent them.
- You may explain widely known federal basics (for example: Housing Choice Vouchers usually require income at or below 50% of area median income, and tenants usually pay about 30% of income toward rent; tax-credit apartments usually cap income at 50-60% of area median income). Say these are general rules and the program sets the final limits.
- State waitlist_status exactly. Never say a waitlist is open unless waitlist_status is "open". If the waitlists the person needs are closed, say so kindly and point to programs that can still help (rent assistance, legal aid, 211).
- availability_status for listings is a website snapshot, not a guaranteed vacancy.
- When you recommend a resource, give its name, phone and how to apply, and mention its source_url.
- Typical documents to prepare: photo ID, Social Security numbers or immigration documents for household members, proof of income (pay stubs, benefit letters), and your current lease or eviction notice. Say the program decides the final list.
- If the person may be unsafe or without shelter tonight, start with: call 911 in an emergency, or 211 for shelter.
- Never ask for or repeat SSNs, bank details or other sensitive data.
- Keep it short and plain: a direct answer first, then up to 5 bullet points. Use **bold** only for names. End with one line saying this is guidance, not legal advice.
- If the question is not about housing, gently steer back to housing help.

Earlier in this conversation:
{past or "(none)"}

Question: {question}

Resources (verified, Northern Virginia):
{json.dumps(resources, ensure_ascii=False)}"""
    return ask_gemma(prompt)


def programs():
    """Verified non-shelter help (vouchers, rent help, legal aid, other services) for the resources page."""
    keep = {"housing_authority", "rental_assistance", "legal_aid", "other"}
    return [_compact(r) for r in load_catalog() if r.get("type") in keep and not isinstance(r.get("availability"), dict)]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(ask(" ".join(sys.argv[1:])))
