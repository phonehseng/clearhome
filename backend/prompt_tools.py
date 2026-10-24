"""Scripts that do the cheap work before Gemma sees anything, so prompts stay small and answers come faster.

- keyword_filters(): reads budget, area, urgency, bedrooms, age, accessibility and resource types from a
  message with plain rules, so the matcher usually doesn't need a separate Gemma call just to parse it.
- compact(): keeps only the fields Gemma needs from catalog records, with long text trimmed.
- document_kind() and lease_excerpt(): decide whether pasted text is a lease or a listing, and keep only
  the lease clauses worth explaining, so long documents don't blow the free tier's token limit.
"""
import re

from advisor import area_for

# Fields that matter for an answer; everything else (photos, review notes, source lists) only costs tokens.
ANSWER_FIELDS = ("name", "type", "jurisdiction", "address", "phone", "hours", "who_it_serves", "cost", "monthly_rent",
                 "bedrooms", "minimum_age", "accessible", "requirements", "how_to_apply", "waitlist_status", "source_url",
                 "rental_space", "price_unit", "rent_basis", "lease_responsibility", "lease_start", "lease_end", "payment_schedule")
MAX_FIELD = 280

TYPE_WORDS = [
    ("rental_listing", r"\b(room|rooms|roommate|roommates|student housing|shared apartment)\b"),
    ("emergency_shelter", r"\b(shelter|tonight|homeless|on the street|nowhere to (go|sleep|stay)|sleep(ing)? in (my|a) car|evicted today|kicked out)\b"),
    ("rental_assistance", r"\b(behind on rent|back rent|can'?t pay|cant pay|rent help|rental assistance|eviction notice|late notice|pay or quit|utility|deposit help)\b"),
    ("legal_aid", r"\b(lawyer|legal|court|evict(ion|ed)?|landlord (won'?t|refuses|is)|my rights|tenant rights|repairs?)\b"),
    ("housing_authority", r"\b(section 8|voucher|hcv|public housing|housing authority|waitlist|wait list)\b"),
    ("affordable_listing", r"\b(apartment|apartments|place to rent|rent a|studio|\d ?(br|bed|bedroom)s?|affordable|low[- ]income|income[- ]restricted|move|listing|unit)\b"),
]
EMERGENCY = r"\b(tonight|right now|nowhere to (go|sleep|stay)|on the street|homeless|evicted today|kicked out|unsafe|in danger)\b"


def keyword_filters(message):
    """Return (filters, confident). confident is False when no need was recognized, so Gemma should parse instead."""
    text = (message or "").lower().replace(",", "")
    types = [t for t, pattern in TYPE_WORDS if re.search(pattern, text)]
    emergency = bool(re.search(EMERGENCY, text))
    if emergency and "emergency_shelter" not in types:
        types.insert(0, "emergency_shelter")
    budget = re.search(r"(?:under|below|less than|at most|max(?:imum)?|up to|budget(?: is| of)?|afford|pay)\s*(?:about\s*)?\$?\s*(\d{3,5})", text) \
        or re.search(r"\$\s*(\d{3,5})", text)
    beds = re.search(r"\b(\d)\s*(?:br|bed|bedroom)", text)
    age = re.search(r"\b(?:i am|i'm|im|age|aged)\s*(\d{2})\b|\b(\d{2})\s*(?:years old|yo)\b", text)
    area = area_for(message)
    filters = {
        "types": types,
        "max_budget_per_month": float(budget.group(1)) if budget else None,
        "needs_accessible": bool(re.search(r"\b(wheelchair|accessible|disab|mobility|ada)\b", text)),
        "urgency": "emergency" if emergency else ("soon" if re.search(r"\b(soon|this month|next month|asap)\b", text) else "planning"),
        "locations": [area] if area else ['__outside_service_area__'],
        "rental_space": 'room' if re.search(r'\b(room|rooms|roommate|roommates)\b', text) else 'all',
        "bedrooms": 0 if "studio" in text else (int(beds.group(1)) if beds else None),
        "age": int(next(g for g in age.groups() if g)) if age else (62 if re.search(r"\b(senior|elderly|retired)\b", text) else None),
    }
    return filters, bool(types)


def compact(rows, limit=10):
    """Only the fields Gemma needs, long text trimmed, at most `limit` records."""
    out = []
    for r in rows[:limit]:
        row = {k: (r[k][:MAX_FIELD] if isinstance(r[k], str) else r[k]) for k in ANSWER_FIELDS if r.get(k) not in (None, "")}
        availability = r.get("availability")
        if isinstance(availability, dict):
            row["availability"] = {"status": availability.get("status"), "checked_on": availability.get("checked_on")}
        else:
            row["last_verified"] = r.get("last_verified")
        out.append(row)
    return out


LISTING_SIGNS = r"\b(dm me|text me|whatsapp|zelle|cash ?app|venmo|gift card|wire|western union|crypto|bitcoin|deposit to hold|out of the country|overseas|mail you the keys|available now|bedroom|br\b|sq ?ft|amenities|move[- ]in special|per month|/mo)\b"
LEASE_SIGNS = r"\b(lease|tenant|landlord|lessor|lessee|premises|term of|security deposit|hereby|shall|agreement|terminat|renew)\b"
LEASE_TOPICS = r"(rent|deposit|fee|late|charge|penalt|terminat|renew|notice|entry|enter|access|repair|mainten|utilit|pet|sublet|sublease|guest|joint|several|evict|default|insur|parking|smok|move[- ]out|refund|increase)"


def document_kind(text):
    """'lease', 'listing' or 'both', from simple word counts; Gemma then only gets the matching instructions."""
    t = (text or "").lower()
    lease = len(re.findall(LEASE_SIGNS, t))
    listing = len(re.findall(LISTING_SIGNS, t))
    if lease >= 3 and listing >= 3:
        return "both"
    return "lease" if lease > listing else "listing"


def lease_excerpt(text, max_chars=6000):
    """For long leases, keep the opening and the clauses about money, dates and rights; drop boilerplate."""
    text = re.sub(r"[ \t]+", " ", text or "").strip()
    if len(text) <= max_chars:
        return text
    pieces = [p.strip() for p in re.split(r"(?<=[.;:])\s+|\n{1,}", text) if p.strip()]
    kept, size = [], 0
    for i, piece in enumerate(pieces):
        if i < 3 or re.search(LEASE_TOPICS, piece, re.I):
            if size + len(piece) > max_chars:
                break
            kept.append(piece)
            size += len(piece) + 1
    return "\n".join(kept) + "\n[Parts of the lease without money, date or rights terms were left out to keep this short.]"
