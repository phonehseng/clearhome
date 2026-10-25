"""Follow-up questions in the chat, with answer buttons, for when a request is missing a detail that would change the answer.

"I need somewhere to live" could mean a rental, a bed tonight or help paying rent, so the chat asks which first, then the
area, then a budget, then (where it changes the results) a room or a whole place and how many bedrooms, one question at a
time, instead of guessing. Each has an "anything is fine" answer, and typing works too. A detailed request ("an entire one-bedroom home in
Blacksburg under $1,200") goes straight to an answer, a general question ("what is a housing voucher?") is just answered,
and someone without a safe place tonight gets 911 and 211 right away, with the area question beside that help, never instead.

No AI decides this: a short script reads the person's own words and what they've already answered. The question goes to
the page as data (field, text, choices), never as HTML. The page keeps this conversation's answers and sends them back with
each message (nothing is stored here), and every field and value is checked against the lists below before it's used.
A newer answer or correction replaces an older one; Skip and Not sure stay unknown, never a guessed value.

Other modules can ask too: question(field, text, choices) builds one, and app.py records it as the open question.
For example, nearby.py could ask which of several stores was meant:
    question("place", "Which Walmart, or which city?", [("Walmart, Christiansburg", "Walmart in Christiansburg"), ...])
The picked value comes back as "near Walmart, Christiansburg" in the request.
"""
import re
import secrets

from advisor import (advice_question, monthly_income, AREAS, BUDGET_ANY, CAMPUS, CHEAP, CLARIFY_MARK, DANGER, LANDMARKS, NEAR_ANY, OUTSIDE, STAY_NOW, URGENT, Instant,
                     area_for, household_size, housing_search, understood, with_context)
from redact import redact

SKIP, UNSURE, ANY = "skip", "unsure", "any"  # "any" is an answer (no preference), not a skipped question
MAX_QUESTIONS = 4  # per request; after four, answer with what's known
QID = re.compile(r"q_[a-z_]{2,24}_[0-9a-f]{8}")


class Question(Instant):
    """A chat reply that asks something, with answer buttons. As a string it's the question's words (for the transcript and
    history); .question is what the page draws: {id, field, text, choices: [{id, label}], multi, skip, unsure, custom}."""
    def __new__(cls, text, asked):
        made = super().__new__(cls, text)
        made.question = asked
        return made


# ---- Fields a question can fill ------------------------------------------------------------------------------
# For each: how to check a value sent back by the page (anything else is dropped), and how to say it in the request.
FIELDS = {}


def register(field, check, phrase=None, multi=False, per_request=False):
    """check(value) -> the value to keep, or None when it isn't valid; phrase(value) -> words added to the request, or None.
    per_request fields (what kind of help, which store) start over with each new request; the rest last the conversation."""
    FIELDS[field] = {"check": check, "phrase": phrase, "multi": multi, "per_request": per_request}


def _one_of(*ids):
    return lambda v: v if isinstance(v, str) and (v in ids or v in (SKIP, UNSURE)) else None


# Places the chat understands: the advisor's place names, well-known landmarks, and the region as a whole.
PLACES = {word: area for word, area in AREAS} | {k: v[0] for k, v in LANDMARKS.items()} | {"northern virginia": "Northern Virginia", "nova": "Northern Virginia"}
NAMES = {"mclean": "McLean", "loudoun": "Loudoun County", "prince william": "Prince William County", "nova": "Northern Virginia", "old town": "Old Town Alexandria"}
_PLACE_WORDS = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(PLACES, key=len, reverse=True)) + r")\b", re.I)
# A rental search can be anywhere in either region; shelters and rent help are run by each county, so those ask which.
RENTAL_AREAS = [("northern virginia", "Northern Virginia"), ("blacksburg", "Blacksburg (Virginia Tech)"), (ANY, "Anywhere is fine")]
AREA_CHOICES = [("blacksburg", "Blacksburg (Virginia Tech)"), ("arlington", "Arlington"), ("alexandria", "Alexandria"),
                ("fairfax county", "Fairfax County"), ("loudoun", "Loudoun County"), ("prince william", "Prince William County")]
CAMPUS_CHOICES = [("virginia tech", "Virginia Tech (Blacksburg)"), ("george mason", "George Mason (Fairfax)"), ("marymount", "Marymount (Arlington)"),
                  ("nova community college", "NOVA Community College (Annandale)")]


def place_name(key):
    return LANDMARKS[key][3] if key in LANDMARKS else NAMES.get(key) or key.title()


def places_in(text):
    """Place keys named in the text, in order, each once ("rooms in Reston or Herndon" -> ["reston", "herndon"])."""
    return list(dict.fromkeys(m.group(1).lower() for m in _PLACE_WORDS.finditer(text or "")))


def _region(key):
    return "Blacksburg" if PLACES[key] == "Blacksburg" else "Northern Virginia"


HELP = {"rental": "I want to find a rental", "tonight": "I need somewhere safe to stay tonight", "rent_help": "I need help paying rent"}
SITUATIONS = [("back_rent", "Rent I'm behind on", "I'm behind on rent", re.compile(r"behind on rent|back rent|owe (?:my )?rent|past due|late rent", re.I)),
              ("eviction", "An eviction notice or court date", "I got an eviction notice or court date", re.compile(r"evict|\bcourt\b", re.I)),
              ("deposit", "A security deposit", "I need help with a security deposit", re.compile(r"\bdeposit", re.I)),
              ("utilities", "Utility bills", "I need help with utility bills", re.compile(r"utilit|electric bill|gas bill|water bill", re.I))]
# Worded so the place searches read them right: only the room answer says "room" (nearby.py filters on that word).
SPACE = {"room": "a room in a shared home (rent is per person)", "entire_home": "a whole apartment or house to myself",
         "either": "no preference between a bedroom in a group rental and a whole home"}
BEDS = {"0": "a studio", "1": "1 bedroom", "2": "2 bedrooms", "3": "3 or more bedrooms", ANY: "any number of bedrooms"}
BASIS = {"total": "the budget is the total for everyone who will live there", "per_person": "the budget is per person"}


def _budget(v):
    if v in ("none", SKIP, UNSURE):
        return v
    if isinstance(v, str) and v.isdigit():
        v = int(v)
    return v if isinstance(v, int) and not isinstance(v, bool) and 100 <= v <= 20000 else None


def _situation(v):
    if v in (SKIP, UNSURE):
        return v
    ids = [k for k, *_ in SITUATIONS]
    if isinstance(v, list) and v and all(isinstance(x, str) and x in ids for x in v):
        return list(dict.fromkeys(v))
    return None


def _place(v):
    """A short place name or address picked from a question's choices (for "which store?" questions)."""
    if v in (SKIP, UNSURE):
        return v
    if isinstance(v, str) and 2 <= len(v.strip()) <= 100 and re.fullmatch(r"[\w .,'#&()/-]+", v.strip()):
        return redact(v.strip())[0]
    return None


register("help", _one_of(*HELP), per_request=True)
register("area", lambda v: v if v in (SKIP, UNSURE, ANY) or (isinstance(v, str) and v in PLACES) else None)
register("budget", _budget)
register("basis", _one_of(*BASIS), lambda v: BASIS.get(v))
register("space", _one_of(*SPACE), lambda v: SPACE.get(v))
register("bedrooms", _one_of(*BEDS), lambda v: BEDS.get(v))
register("situation", _situation, lambda v: "; ".join(p for k, _, p, _ in SITUATIONS if k in v) if isinstance(v, list) else None,
         multi=True, per_request=True)
register("place", _place, lambda v: None if v in (SKIP, UNSURE) else f"near {v}", per_request=True)


def question(field, text, choices, multi=False, skip=True, unsure=False, custom=True, intro=""):
    """A question for the chat to ask with answer buttons. choices: [(value, label)], up to 8; a value that fails the field's
    check is left out, so anything the person can pick is already a valid answer. Raises KeyError for an unregistered field.
    Return it as the chat's answer: app.py sends it to the page and records it as the open question."""
    spec = FIELDS[field]
    multi = multi or spec["multi"]
    picks = [{"id": str(v), "label": str(label)[:80]} for v, label in choices
             if spec["check"]([str(v)] if multi else str(v)) is not None][:8]
    asked = {"id": f"q_{field}_{secrets.token_hex(4)}", "field": field, "text": text, "choices": picks,
             "multi": multi, "skip": skip, "unsure": unsure, "custom": custom}
    return Question(f"{intro} {text}".strip(), asked)


# ---- Reading what was said -------------------------------------------------------------------------------------
TONIGHT = re.compile(r"\b(emergency (?:housing|shelters?|places? to (?:stay|sleep)|beds?|rooms?)|crisis housing|need (?:a place|somewhere|housing) (?:now|today|asap|right now|immediately)|tonight|shelters?|homeless|nowhere to (?:go|sleep|stay)|on the street|sleep(?:ing)? in (?:my|a) car|kicked out|"
                     r"somewhere safe|safe place to (?:stay|sleep))\b", re.I)
RENT_HELP = re.compile(r"\b(rent help|help (?:with|paying) (?:my |the )?rent|rent(?:al)? assistance|pay(?:ing)? (?:my |the )?rent|behind on rent|"
                       r"back rent|owe (?:my )?rent|evict\w*|security deposit|utility bills?|los(?:e|ing) (?:my|our|the) (?:apartment|home|house|place|housing)|can'?t afford (?:my |the )?rent)\b", re.I)
RENTAL = re.compile(r"\b(apartments?|rentals?|for rent|to rent|rooms?|studios?|townhouses?|condos?|duplex|sublets?|subleases?|"
                    r"low[- ]income|affordable|income[- ](?:based|restricted)|subsidi[sz]ed)\b", re.I)
BEDROOMS = re.compile(r"\b(?:\d|one|two|three|four)[- ]?(?:bed(?:room)?s?|br|bd)\b", re.I)
# "I need somewhere to live", "I need help": a need without the kind of help. Named topics (vouchers, a landlord) are not vague.
VAGUE = re.compile(r"\b(somewhere|a place|housing|a home|new home|help|move|moving|relocat\w*)\b", re.I)
SPECIFIC = re.compile(r"\b(vouchers?|section 8|hcv|public housing|wait ?lists?|housing authority|landlords?|lawyers?|legal|rights|repairs?|"
                      r"court|seniors?|elderly|veterans?|deposit|utilit\w*|mortgage|buy(?:ing)?|food|jobs?)\b", re.I)
# A general question gets an answer, not a questionnaire. "Where can I find an apartment?" is a search, so "where" isn't here.
GREETING = re.compile(r"^\s*(?:hi+|hello|hey+|hiya|howdy|yo|hola|good (?:morning|afternoon|evening)|sup|what'?s up)\b[\s!.?,]*(?:there|gemma)?[\s!.?]*$", re.I)
INFO = re.compile(r"^\s*(what|what's|whats|how|why|who|explain|define|tell me about|is there|are there|does|do i|do you|do they|is it|is a|is an|are)\b", re.I)
NO_BUDGET = re.compile(r"\b(no (?:set |real )?budget|any (?:price|budget)|price doesn'?t matter|whatever it costs)\b", re.I)
BARE_NUMBER = re.compile(r"\$?\s*(\d{3,5})(?:\s*(?:a|per|/)\s*(?:month|mo))?")
BUDGET_TEXT = re.compile(r"(?:under|below|less than|at most|max(?:imum)?|up to|budget(?: is| of)?|afford|around|about|\$)\s*\$?\s*\d{3,5}(?!\d)"
                         r"(?:\s*(?:a|per|/)\s*(?:month|mo)\b)?", re.I)
PER_PERSON = re.compile(r"\bper (?:person|head)\b|\beach (?:person|of us)\b", re.I)
TOTAL = re.compile(r"\b(?:total|combined)\b|\bfor (?:both|all) of us\b", re.I)
NOT_SPACE = re.compile(r"\b(?:not|no|don'?t want|do not want|don'?t need|do not need|never|without|instead of)\s+(?:a\s+|an\s+|the\s+|just\s+a\s+|any\s+)?"
                       r"(?:shared\s+)?(?:rooms?|roommates?|(?:whole|entire)\s+(?:place|apartment|home|house|unit)|(?:apartment|place|home|house)\s+to\s+myself)\b", re.I)
ROOM = re.compile(r"\b(?:rooms?|roommates?|shared (?:apartment|house|home|room))\b", re.I)
WHOLE = re.compile(r"\b(?:entire|whole (?:place|apartment|home|house|unit)|my own place|to myself|studios?|townhouses?|condos?|"
                   r"(?:\d|one|two|three|four)[- ]?(?:bed(?:room)?s?|br|bd))\b", re.I)
EITHER = re.compile(r"\b(either|both|no preference|doesn'?t matter)\b", re.I)
ANYTHING = re.compile(r"(?:any|anything|anywhere|whatever|doesn'?t matter|no preference)(?: (?:size|budget|price|area|place|amount))?"
                      r"(?: (?:is )?(?:fine|ok|okay|works))?", re.I)
_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4}
SKIP_WORDS = re.compile(r"(skip|skip (?:it|this|this one|that)|pass|rather not say|prefer not to say)", re.I)
UNSURE_WORDS = re.compile(r"(not sure|unsure|i'?m not sure|i don'?t know|idk|dunno|no idea|no preference|anywhere|either)", re.I)


# A yearly rent budget ("$12,000 total a year") is rewritten as its monthly amount, so every step after this (the
# questions, the request Gemma reads, the place searches) uses the same number: "$1000 total a month (12000 dollars per
# year)". The note in brackets is worded so it isn't read as a budget again. An income ("I make $30,000 a year") isn't a
# budget, and a weekly amount isn't guessed at: the budget question asks instead.
YEARLY = re.compile(r"(\$?)(\d{4,6})(?!\d)(\s*(?:total\s+|in total\s+|combined\s+)?)(?:a|per|each|every|/)\s*(?:year|yr)\b"
                    r"|(\$?)(\d{4,6})(?!\d)\s*(?:annually|yearly)\b", re.I)
WEEKLY = re.compile(r"\s*(?:total\s+)?(?:a|per|each|every|/)\s*(?:week|wk)\b|\s*weekly\b", re.I)
EARNINGS = re.compile(r"\b(?:income|make|makes|making|earn|earns|earning|salary|wages?|paid|paycheck)\b[^.;!?$]{0,25}\$?\s*$", re.I)


def _monthly(text):
    def per_month(m):
        sign, amount, middle = (m.group(1), m.group(2), m.group(3) or " ") if m.group(2) else (m.group(4), m.group(5), " ")
        if EARNINGS.search(text[max(0, m.start() - 40):m.start()]):
            return m.group(0)
        return f"{sign}{round(int(amount) / 12)}{middle}a month ({amount} dollars per year)"
    return YEARLY.sub(per_month, text)


def _plain(text):
    """$1,200 -> $1200 and a yearly budget -> its monthly amount, so budgets read the same however they're typed."""
    return _monthly(re.sub(r"(?<=\d),(?=\d{3}\b)", "", text or ""))


def _budget_in(t):
    """The first rent budget in the words: not an income, not a weekly amount, and in range."""
    for m in BUDGET_ANY.finditer(t):
        if _budget(int(m.group(1))) and not WEEKLY.match(t[m.end():]) and not EARNINGS.search(t[max(0, m.start() - 40):m.end() - len(m.group(1))]):
            return int(m.group(1))
    return None


def detect_help(text):
    """The kind of help the words ask for: rental, tonight or rent_help, or None when they don't say."""
    t = _plain(text)
    if TONIGHT.search(t) or DANGER.search(t) or STAY_NOW.search(t):
        return "tonight"
    if RENT_HELP.search(t):
        return "rent_help"
    if housing_search(t) or RENTAL.search(t) or BEDROOMS.search(t):
        return "rental"
    return None


def read_fields(text, pending=None):
    """Answers stated in these words, like {"area": "reston", "budget": 1200}. While a question is open, a bare reply to it
    counts too ("1200", "skip", "either")."""
    t = _plain(text)
    found = {}
    keys = places_in(t)
    if keys and len({_region(k) for k in keys}) == 1:  # Blacksburg and Arlington at once is a conflict, asked about instead
        found["area"] = next((k for k in keys if k in LANDMARKS), keys[0])
    budget = _budget_in(t)
    if budget:
        found["budget"] = budget
    elif NO_BUDGET.search(t):
        found["budget"] = "none"
    if PER_PERSON.search(t):
        found["basis"] = "per_person"
    elif TOTAL.search(t):
        found["basis"] = "total"
    # "Not a room, an entire apartment": what they said no to doesn't count. Both still named ("a room or a whole place")
    # is no preference read from the words, so the room-or-whole-place question asks.
    kept = NOT_SPACE.sub(" ", t)
    room, whole = bool(ROOM.search(kept)), bool(WHOLE.search(kept))
    if room != whole:
        found["space"] = "room" if room else "entire_home"
    beds = BEDROOMS.search(t)
    if beds:
        n = re.match(r"\d|[a-z]+", beds.group(0).lower()).group(0)
        found["bedrooms"] = str(min(int(n) if n.isdigit() else _WORD_NUMBERS[n], 3))
    elif re.search(r"\bstudios?\b", t, re.I):
        found["bedrooms"] = "0"
    hits = [k for k, _, _, pattern in SITUATIONS if pattern.search(t)]
    if hits:
        found["situation"] = hits
    bare = t.strip(" .!?").lower()
    if pending and pending not in found:
        if pending == "space" and (EITHER.search(bare) or ANYTHING.fullmatch(bare)):
            found["space"] = "either"
        elif pending in ("area", "bedrooms") and ANYTHING.fullmatch(bare):
            found[pending] = ANY
        elif pending == "budget" and ANYTHING.fullmatch(bare):
            found["budget"] = "none"
        elif SKIP_WORDS.fullmatch(bare):
            found[pending] = SKIP
        elif UNSURE_WORDS.fullmatch(bare):
            found[pending] = UNSURE
        elif pending == "budget" and BARE_NUMBER.fullmatch(bare) and _budget(int(BARE_NUMBER.fullmatch(bare).group(1))):
            found["budget"] = int(BARE_NUMBER.fullmatch(bare).group(1))
        elif pending == "help" and detect_help(t):
            found["help"] = detect_help(t)
    return found


def _profile_area(profile):
    location = (profile or {}).get("location")
    return isinstance(location, str) and location.strip() and area_for(location)


# ---- The conversation's answers, as the page sends them back --------------------------------------------------
def load_state(raw):
    """This conversation's answers as the page returned them, keeping only fields and values this module accepts."""
    raw = raw if isinstance(raw, dict) else {}
    answers = {}
    for field, value in (raw.get("answers") if isinstance(raw.get("answers"), dict) else {}).items():
        kept = FIELDS[field]["check"](value) if field in FIELDS else None
        if kept is not None:
            answers[field] = kept
    request = raw.get("request")
    request = redact(request.strip()[:1500])[0] if isinstance(request, str) and request.strip() else None
    asked = [f for f in raw.get("asked") if isinstance(f, str) and f in FIELDS] if isinstance(raw.get("asked"), list) else []
    pending = raw.get("pending")
    if not (isinstance(pending, dict) and isinstance(pending.get("field"), str) and pending["field"] in FIELDS and isinstance(pending.get("id"), str)
            and QID.fullmatch(pending["id"]) and pending["id"].startswith(f"q_{pending['field']}_")):
        pending = None
    return {"request": request, "answers": answers, "asked": list(dict.fromkeys(asked))[:8],
            "pending": pending and {"id": pending["id"], "field": pending["field"]}}


def known(state, field):
    """A real answer for this field (not Skip or Not sure)."""
    return bool(state) and state["answers"].get(field) not in (None, SKIP, UNSURE)


def record(state, asked, request=None):
    """Remember that this question is now the open one (so only a reply to it counts)."""
    q = asked.question
    state["pending"] = {"id": q["id"], "field": q["field"]}
    if q["field"] not in state["asked"]:
        state["asked"].append(q["field"])
    if request:
        state["request"] = request[:1500]


class Stale(ValueError):
    """A button answer to a question that's no longer the open one (answered already, or a newer one was asked)."""


def apply_reply(state, reply):
    """A button answer, {"id": question id, "choices": [choice ids]}, written into the answers."""
    pending = state["pending"]
    if not isinstance(reply, dict) or not pending or reply.get("id") != pending["id"]:
        raise Stale("That question was already answered. Pick from the latest question, or type your answer.")
    picks = [p for p in reply.get("choices") if isinstance(p, str)][:8] if isinstance(reply.get("choices"), list) else []
    field = pending["field"]
    value = picks[0] if len(picks) == 1 and picks[0] in (SKIP, UNSURE) else picks if FIELDS[field]["multi"] else picks[0] if len(picks) == 1 else None
    value = FIELDS[field]["check"](value) if value is not None else None
    if value is None:
        raise ValueError("That answer isn't one of the choices. Pick one, or type your answer.")
    state["answers"][field] = value
    state["pending"] = None


def _read_typed(text, state):
    """Which request a typed message belongs to, after writing the answers it states into the state."""
    pending = state["pending"] and state["pending"]["field"]
    found = read_fields(text, pending)
    own = detect_help(text) or INFO.match(text) or URGENT.search(text)  # a request of its own
    short = len(text.split()) <= 8
    if state["request"] and ((pending and pending in found) or (not own and (pending or (found and short)))):
        # A reply to the open question, or a short correction ("actually Alexandria", "under 1200"): the same request,
        # and the newer answers win. Longer replies keep their own words with the request too.
        state["answers"].update(found)
        state["pending"] = None
        return state["request"] if len(text.split()) <= 3 else f"{state['request'].rstrip(' .?!')}; {text}"
    # A new request: what it says replaces older answers; what it leaves out (area, budget) is still remembered.
    for field, spec in FIELDS.items():
        if spec["per_request"]:
            state["answers"].pop(field, None)
    if len({_region(k) for k in places_in(_plain(text))}) > 1:
        state["answers"].pop("area", None)  # two regions at once: ask which instead of keeping an older answer
    state["answers"].update(found)
    state["asked"], state["pending"] = [], None
    return text


# ---- Deciding what to ask -------------------------------------------------------------------------------------
TONIGHT_HELP = "If you're in danger right now, call **911**. For a shelter bed tonight, call **211** (free, any hour); they connect you to intake."
OUTSIDE_NOTE = "Clear Home only covers Northern Virginia and Blacksburg, so I can't search there. For housing help where you are, call **211**."


def _area_question(kind, conflict=None, intro=""):
    if conflict:
        a, b = (place_name(k) for k in conflict[:2])
        return question("area", "Which should I search?", [(k, place_name(k)) for k in conflict[:2]], intro=f"You mentioned {a} and {b}.")
    if kind == "tonight":
        return question("area", "Where are you tonight? I'll show shelters, intake lines and hotels nearby.", AREA_CHOICES,
                        skip=False, unsure=True, intro=f"{intro} {TONIGHT_HELP}".strip())
    if kind == "rent_help":
        return question("area", "Where do you live? Rent help is run by each city and county.", AREA_CHOICES, skip=True, unsure=True, intro=intro)
    return question("area", "Where are you looking? Pick one, or type a city or neighborhood.", RENTAL_AREAS, skip=False, intro=intro)


def next_question(request, state, profile=None):
    """The one question that would most change the answer to this request, or None to answer now."""
    a, profile, t = state["answers"], profile or {}, _plain(request)
    if len(state["asked"]) >= MAX_QUESTIONS or INFO.match(t) or profile.get("tonight") or advice_question(t):
        return None  # questions and advice are answered, not asked about
    if GREETING.match(t) and "help" not in state["asked"]:  # "hi": the three kinds of help, as buttons
        return question("help", "Hi, I'm Gemma. What kind of help do you need first?", [(k, label) for k, label in
                        (("rental", "Find a rental"), ("tonight", "Somewhere safe tonight"), ("rent_help", "Help paying rent"))],
                        skip=False, unsure=True)
    free = lambda field: field not in a and field not in state["asked"]  # not answered, and not asked yet for this request
    kind = a.get("help") or detect_help(t)
    if kind is None:
        vague = VAGUE.search(t) and not SPECIFIC.search(t) and len(t.split()) <= 15
        return question("help", "What kind of help do you need first?", [(k, label) for k, label in
                        (("rental", "Find a rental"), ("tonight", "Somewhere safe tonight"), ("rent_help", "Help paying rent"))],
                        skip=False, unsure=True) if vague and free("help") else None
    if kind in (SKIP, UNSURE) or (URGENT.search(t) and kind != "tonight"):
        return None  # behind on rent, an eviction, someone unsafe: answered right away
    keys = places_in(t)
    conflict = keys if len({_region(k) for k in keys}) > 1 and "area" not in a else None
    has_area = "area" in a or bool(keys and not conflict) or _profile_area(profile)
    away = OUTSIDE_NOTE if not keys and re.search(OUTSIDE, t, re.I) else ""  # "apartments in Richmond": say we don't cover it
    if away and not has_area and free("area"):  # even "near UVA", before any place search
        return _area_question(kind if kind in ("tonight", "rent_help") else "rental", intro=away)
    if kind == "tonight":  # shelter intake is run by each county, so "Northern Virginia" alone asks which
        specific = (a.get("area") not in (None, "northern virginia", "nova", ANY)) or any(k not in ("northern virginia", "nova") for k in keys) or _profile_area(profile)
        return _area_question("tonight", intro=away) if not specific and "area" not in state["asked"] else None
    if kind == "rent_help":
        if not has_area and free("area"):
            return _area_question("rent_help", conflict, intro=away)
        if free("situation") and not any(p.search(t) for *_, p in SITUATIONS):
            return question("situation", "What do you need help paying? Pick all that apply.",
                            [(k, label) for k, label, *_ in SITUATIONS], multi=True, skip=False, unsure=True)
        return None
    # A rental: where and a budget whenever they're missing, then (where it changes the results) a room or a whole place,
    # and how many bedrooms. Each has an "anything is fine" answer. "Near my office at ..." names its own place
    # (nearby.py and near_place.py find it), except a bare "campus".
    near = NEAR_ANY.search(t) and not CAMPUS.search(t)
    if not has_area and free("area") and not near:
        if CAMPUS.search(t) and not conflict:
            return question("area", CLARIFY_MARK, CAMPUS_CHOICES, skip=False, unsure=True,
                            intro=f"Got it: a place {', '.join(understood(t))}.")
        return _area_question("rental", conflict, intro=away)
    budget = a.get("budget") or (isinstance(profile.get("budget"), (int, float)) and not isinstance(profile["budget"], bool) and profile["budget"] > 0 and int(profile["budget"]))
    area = a.get("area") if a.get("area") in PLACES else (keys[0] if keys and not conflict else None)
    region = _region(area) if area else ("Blacksburg" if _profile_area(profile) == "Blacksburg" else "Northern Virginia" if _profile_area(profile) else None)
    voucher = re.search(r"\b(?:vouchers?|section ?8|hcv)\b", t, re.I)  # a voucher sets what they pay
    if not budget and not CHEAP.search(t) and not voucher and not monthly_income(t) and free("budget"):  # income: Gemma uses about 30% of it  # "the cheapest" already says how to sort
        steps = {"Blacksburg": (600, 900, 1300), "Northern Virginia": (1200, 1800, 2500)}.get(region, (800, 1500, 2500))
        return question("budget", "About how much can you pay each month for rent?",
                        [(str(steps[0]), f"Under ${steps[0]:,}")] + [(str(hi), f"${lo:,}–${hi:,}") for lo, hi in zip(steps, steps[1:])]
                        + [("none", "Any budget is fine")], skip=False)
    people = household_size(t) or (profile.get("household") if isinstance(profile.get("household"), int) else None)
    if isinstance(budget, int) and people and people > 1 and free("basis"):
        return question("basis", f"Is ${budget:,} your total monthly budget or per person?",
                        [("total", "Total for everyone"), ("per_person", "Per person")], skip=False, unsure=True)
    if near:
        return None  # a place search is specific enough; its own questions (which store?) come next
    if region == "Blacksburg" and free("space"):  # student rooms are priced per person, whole places per home
        return question("space", "A room in a shared home, or a whole place?",
                        [("room", "A room (rent is per person)"), ("entire_home", "A whole place"), ("either", "Anything is fine")], skip=False)
    whole = a.get("space") == "entire_home" or (region == "Northern Virginia" and a.get("space") != "room")
    if whole and profile.get("bedrooms") is None and free("bedrooms"):
        return question("bedrooms", "How many bedrooms?", [("0", "Studio"), ("1", "1 bedroom"), ("2", "2 bedrooms"), ("3", "3 or more"),
                                                           (ANY, "Any size is fine")], skip=False)
    return None


# ---- Writing the answers into the request ---------------------------------------------------------------------
BROAD = "no particular area, so give broad results across Northern Virginia, say they're broad, and that naming a city or Blacksburg narrows them"


def compose(request, answers):
    """The request with this chat's answers written in. An answer replaces what it corrects in the request's own words
    (a new budget, a different city); the rest is added after it. General questions are left as asked."""
    t = _plain(request)
    if INFO.match(t):
        return request
    own = read_fields(t)  # what the request already says needs no repeating (and a request left as typed keeps its saved answer)
    answers = {k: v for k, v in answers.items() if own.get(k) != v}
    kind = answers.get("help") if answers.get("help") in HELP else detect_help(t)
    notes = []
    if answers.get("help") in HELP and detect_help(t) != answers["help"]:
        notes.append(HELP[answers["help"]])
    elif answers.get("help") == UNSURE:
        notes.append("I'm not sure yet what kind of help I need, so briefly explain the main options (finding a rental, "
                     "a safe place tonight, help paying rent) and ask which fits")
    area = answers.get("area")
    if kind and area in PLACES:
        name, said = place_name(area), places_in(t)
        if [k for k in said if k != area]:  # "in Blacksburg or Arlington", answered Arlington: "in Arlington"
            t = _PLACE_WORDS.sub(lambda m: m.group(0) if m.group(1).lower() == area else name, t)
            t = re.sub(rf"\b({re.escape(name)})(?:\s*(?:,|/|\bor\b|\band\b)\s*\1\b)+", r"\1", t, flags=re.I)
        elif not said and CAMPUS.search(t):
            t = CAMPUS.sub(name if area in LANDMARKS else lambda m: f"{m.group(0)} in {name}", t, count=1)
        elif not said and not NEAR_ANY.search(t):
            notes.append(f"{'near' if area in LANDMARKS else 'in'} {name}")
    elif kind and area in (SKIP, UNSURE, ANY) and not places_in(t):
        notes.append(BROAD)
    if kind == "rental":
        budget = answers.get("budget")
        if isinstance(budget, int):
            t, n = BUDGET_TEXT.subn(f"under ${budget}", t)
            if not n:
                notes.append(f"under ${budget} a month")
        elif budget == "none":
            t = BUDGET_TEXT.sub("", t)
            notes.append("no set budget")
        elif budget in (SKIP, UNSURE) and not BUDGET_TEXT.search(t):
            notes.append("no budget given, so don't assume one")
    for field, spec in FIELDS.items():
        if field in ("help", "area", "budget") or field not in answers or not spec["phrase"]:
            continue
        if (field in ("basis", "space", "bedrooms") and kind != "rental") or (field == "situation" and kind != "rent_help"):
            continue
        words = spec["phrase"](answers[field])
        if words:
            notes.append(words)
    if not notes and t == _plain(request):
        return request
    t = re.sub(r"\s{2,}", " ", t).strip()
    return f"{t.rstrip(' .?!;')}. My answers in this chat: {'; '.join(notes)}." if notes else t


def reply_in_words(text, state, history=None):
    """A reply to a question asked in words only (near_place.py's "Which Walmart, or which city?") keeps the request it
    answers, with this chat's answers in it: the message before may have been a button answer like "Under $1,200"."""
    if state["pending"]:
        return text  # a question with buttons is open: resolve() reads the reply
    last = (history or [])[-1:]
    if state["request"] and last and last[0].get("role") == "assistant":
        return with_context(text, [{"role": "user", "text": compose(state["request"], state["answers"])}, last[0]])
    return with_context(text, history)


def resolve(text, state, profile=None, reply=None):
    """Decide one chat message: (Question, request) to ask first, or (None, request with the answers written in) to answer.
    reply is a button answer to the open question. state is updated in place; the page gets it back for the next message."""
    pending = state["pending"] and state["pending"]["field"]
    if reply is not None:
        apply_reply(state, reply)
        request = state["request"] or text
    else:
        request = _read_typed(text, state)
        if pending == "area" and "area" not in state["answers"] and re.search(OUTSIDE, text, re.I):
            asked = _area_question(state["answers"].get("help") or detect_help(request), intro=OUTSIDE_NOTE)  # a place we don't cover: ask again
            record(state, asked, request)
            return asked, request
    asked = next_question(request, state, profile)
    state["request"] = request[:1500]
    if asked:
        record(state, asked)
        return asked, request
    return None, compose(request, state["answers"])
