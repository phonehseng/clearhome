"""Small web server: serves the page in frontend/ and the /api endpoints.

Run:  python backend/app.py      then open http://localhost:8000 (about page) or /app (tools)
Set INCLUDE_UNVERIFIED=1 to also use placeholder entries while testing.
"""
import gzip
import json
import os
import math
import threading
from datetime import date

from flask import Flask, Response, g, jsonify, request, send_from_directory, send_file, stream_with_context

from limits import limited
from advisor import (AREAS, about_answer, advice_question, ask, boundary_answer, cards_for, clarify, expand_nicknames, fair_housing_answer,
                     named_answer, options, social_answer, outside_answer, programs, quick_nearby, stream_ask, warm_examples, with_context)
import clarifier
import crisis
from live_search import search as live_search
import hotels
import sorter
import nearby
import near_place
import walkable
from matcher import gemma_unavailable, find_help
from catalog import REVIEW_PATH, REVIEW_STATES, filter_catalog, group_listings, load_catalog, load_reviews, validate_resources, STATUSES
from listing_photos import CARD_WIDTHS, card_photo, cached_photo, photo_mimetype, PhotoUnavailable
from redact import redact
from sources import refresh_in_background
from freshness import check_in_background

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
# Cloud Run's disk resets on every restart, so the hosted copy never writes data files.
READ_ONLY = os.environ.get("CLEARHOME_READ_ONLY") == "1"
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # requests are small JSON; no uploads


# Every response: no framing by other sites (clickjacking), no MIME sniffing, HTTPS only, and no plugins or <base> tricks.
# A full script allowlist (CSP) is left out: Maps, Leaflet and the fonts load from several hosts.
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Content-Security-Policy": "frame-ancestors 'self'; object-src 'none'; base-uri 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(self), camera=(), microphone=(), payment=()",
}


@app.after_request
def security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


@app.after_request
def compress(response):
    """Gzip pages and JSON (the listings JSON shrinks about 13x). Streamed chat answers and photos are left alone."""
    if (response.status_code != 200
            or "Content-Encoding" in response.headers or "gzip" not in request.headers.get("Accept-Encoding", "")
            or not (response.mimetype or "").startswith(("application/json", "text/html", "text/css", "text/javascript", "application/javascript", "image/svg"))):
        return response
    response.direct_passthrough = False  # page files are small enough to read and compress
    data = response.get_data()
    if len(data) < 1024:
        return response
    response.set_data(gzip.compress(data, compresslevel=6))
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Vary"] = "Accept-Encoding"
    return response


@app.get("/logo.svg")
def logo():
    return send_from_directory(FRONTEND, "logo.svg")


@app.get("/favicon.svg")
@app.get("/favicon.ico")
@app.get("/apple-touch-icon.png")
def site_icon():
    """The Clear Home logo as the browser-tab and home-screen icon."""
    name = request.path.lstrip("/")
    return send_from_directory(FRONTEND, name, max_age=86400)


@app.get("/images/<path:name>")
def images(name):
    """Site artwork, like the region maps shown on listings that have no photo yet."""
    return send_from_directory(os.path.join(FRONTEND, "images"), name, max_age=86400)


@app.get("/")
def about():
    return send_from_directory(FRONTEND, "about.html")


@app.get("/app")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/videos/<path:name>")
def videos(name):
    """The front page's map recording and its poster; range requests let the page scrub through the video."""
    return send_from_directory(os.path.join(FRONTEND, "videos"), name, max_age=86400, conditional=True)


@app.get("/assets/<path:name>")
def page_assets(name):
    """Each page's own styles and scripts (frontend/assets/<page>/). Browsers check back each visit (a quick 304 when
    nothing changed), so an edited file is live after a deploy without renaming it."""
    response = send_from_directory(os.path.join(FRONTEND, "assets"), name, conditional=True)
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.get('/listing-map.js')
def listing_map_js():
    return send_from_directory(FRONTEND, 'listing-map.js')


@app.get('/rental-labels.js')
def rental_labels():
    return send_from_directory(FRONTEND, 'rental-labels.js')


@app.get('/interface.css')
def interface_styles():
    return send_from_directory(FRONTEND, 'interface.css')


@app.get('/site-header.css')
def site_header_styles():
    return send_from_directory(FRONTEND, 'site-header.css')


@app.get('/site-header.js')
def site_header_js():
    return send_from_directory(FRONTEND, 'site-header.js')


@app.get("/media/listings/<resource_id>")
def listing_photo(resource_id):
    # IDs resolve to trusted catalog metadata; arbitrary URLs are never accepted.
    row = next((row for row in load_catalog() if row.get('id') == resource_id), None)
    if not row or not row.get('photo'):
        return jsonify(error="No provider photo is available for this listing."), 404
    # ?w=800: the smaller copy the listing cards use; without it, the original (when someone enlarges the photo).
    width = request.args.get('w', type=int)
    if width is not None and width not in CARD_WIDTHS:
        return jsonify(error="w must be one of " + ", ".join(map(str, sorted(CARD_WIDTHS))) + "."), 400
    try:
        path = card_photo(row['photo'], width) if width else cached_photo(row['photo'])
        response = send_file(path, mimetype=photo_mimetype(path), max_age=86400, conditional=True)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    except (PhotoUnavailable, OSError):
        response = jsonify(error="Provider photo unavailable. Use the listing's photo-source link.")
        response.status_code = 503
        response.headers['Cache-Control'] = 'no-store'
        return response


@app.get("/api/listings")
def listings():
    """Browse the reviewed catalog without an AI call or API key."""
    grouping = request.args.get('group_by', '')
    sort = request.args.get('sort', 'recommended')
    if grouping not in {'', 'community'}:
        return jsonify(error='group_by must be community when supplied.'), 400
    if sort not in {'recommended', 'rent_asc'}:
        return jsonify(error='sort must be recommended or rent_asc.'), 400
    housing_type = request.args.get("housing_type", "all")
    category_types = {"all": ["affordable_listing", "rental_listing", "housing_authority"], "affordable": ["affordable_listing", "housing_authority"], "regular": ["rental_listing"]}
    if housing_type not in category_types:
        return jsonify(error="housing_type must be all, affordable, or regular."), 400
    filters = {"types": category_types[housing_type]}
    for query, choices in (('rental_space', {'all', 'room', 'entire_home'}),
                           ('age_group', {'all', 'general', 'senior'})):
        value = request.args.get(query, 'all')
        if value not in choices:
            return jsonify(error=f"Unsupported {query} filter."), 400
        filters[query] = value
    location = request.args.get("location", "").strip()
    if location:
        filters["locations"] = [location]
    for query, field in (("max_rent", "max_budget_per_month"), ("bedrooms", "bedrooms"), ("age", "age")):
        value = request.args.get(query)
        if value is None:
            continue
        try:
            parsed = float(value)
            if not math.isfinite(parsed) or parsed < 0 or (query != "max_rent" and not parsed.is_integer()):
                raise ValueError
        except ValueError:
            return jsonify(error=f"{query} must be a nonnegative {'number' if query == 'max_rent' else 'integer'}."), 400
        filters[field] = parsed if query == "max_rent" else int(parsed)
    accessible = request.args.get("accessible", "false").lower()
    if accessible not in {"true", "false"}:
        return jsonify(error="accessible must be true or false."), 400
    filters["needs_accessible"] = accessible == "true"
    status = request.args.get("status")
    if status is not None and status not in STATUSES - {"closed"}:
        return jsonify(error="Unsupported active availability status."), 400
    # Browsing shows homes and waitlists with availability evidence, not shelters or programs.
    rows = [r for r in filter_catalog(load_catalog(), filters) if isinstance(r.get("availability"), dict)]
    if status:
        rows = [r for r in rows if r.get("availability", {}).get("status") == status]
    option_count = len(rows)
    if request.args.get('fields') == 'pins':  # the map only needs a pin and a popup
        rows = [{k: r.get(k) for k in PIN_FIELDS} | {'availability': {'status': r['availability'].get('status')}}
                for r in rows if isinstance(r.get('lat'), (int, float))]
    elif grouping == 'community':
        rows = [_slim_card(card) for card in group_listings(rows, sort=sort)]
    else:
        if sort == 'rent_asc':
            rows.sort(key=lambda row: (row.get('monthly_rent') is None, row.get('monthly_rent') or 0))
        rows = [_slim(r) for r in rows]
    return jsonify(listings=rows, count=len(rows), option_count=option_count, notice="Official-source web review, not a live vacancy feed. Confirm rent, eligibility and availability directly. Closed or overdue records are excluded.")


@app.get("/api/coverage")
def coverage():
    """The front page's 'What's in the list' counts, taken from the same reviewed catalog the app serves."""
    rows = load_catalog()
    # Communities as the listings page counts them: homes and waitlists, floor plans grouped (senior-only included).
    browsable = [r for r in filter_catalog(rows, {"types": ["affordable_listing", "rental_listing", "housing_authority"]}) if isinstance(r.get("availability"), dict)]
    return jsonify(records=len(rows), communities=len(group_listings(browsable)), shelters=sum(r.get("type") == "emergency_shelter" for r in rows),
                   legal_aid=sum(r.get("type") == "legal_aid" for r in rows),
                   with_rent=sum(r.get("monthly_rent") is not None for r in rows), as_of=date.today().isoformat())


# Bookkeeping fields no page shows; leaving them out keeps the listings response small.
INTERNAL_FIELDS = {'catalog_batch', 'verification_method', 'geocode_source', 'source_link_audit', 'review_notes', 'currency', 'record_kind'}
PIN_FIELDS = ('id', 'community', 'name', 'floor_plan', 'lat', 'lon', 'monthly_rent', 'rent_basis', 'rental_space', 'source_url')


def _slim(row):
    return {k: v for k, v in row.items() if k not in INTERNAL_FIELDS}


def _slim_card(card):
    """A grouped card whose floor plans list only what differs from the card; pages merge them back as {...card, ...plan}."""
    card = _slim(card)
    plans = card.pop('floor_plans', [])
    card['floor_plans'] = [{k: v for k, v in _slim(p).items() if card.get(k) != v} | {k: None for k in card if k not in p and k not in INTERNAL_FIELDS}
                           for p in plans]
    return card


@app.get("/resources")
def resources_page():
    return send_from_directory(FRONTEND, "resources.html")


@app.get("/review")
def review_page():
    return send_from_directory(FRONTEND, "review.html")


@app.get("/google-cloud")
def google_cloud_page():
    return send_from_directory(FRONTEND, "google-cloud.html")


_review_lock = threading.Lock()
REVIEW_FIELDS = ('id', 'name', 'community', 'floor_plan', 'type', 'jurisdiction', 'area', 'region', 'address', 'phone',
                 'monthly_rent', 'rent_basis', 'source_url', 'website', 'last_verified', 'minimum_age', 'lat', 'lon')


def _can_review():
    """Decisions are saved to data/listing_review.json, so only on a teammate's own computer (never the hosted site)."""
    return not READ_ONLY and request.remote_addr in {"127.0.0.1", "::1"}


@app.get("/api/review")
def review_list():
    """Every record (shown or not) with the team's decision on it, for the hand-review page."""
    shown = {r['id'] for r in filter_catalog(load_catalog())}
    rows = []
    for r in load_catalog(include_unverified=True):
        if not isinstance(r, dict) or not r.get('id'):
            continue
        avail = r.get('availability') if isinstance(r.get('availability'), dict) else {}
        rows.append({k: r.get(k) for k in REVIEW_FIELDS} | {
            'availability': {k: avail.get(k) for k in ('status', 'checked_on', 'review_due', 'available_from', 'evidence')},
            'verified': r.get('verified') is True, 'problems': validate_resources([r])[:3], 'shown': r['id'] in shown,
            'has_photo': bool(r.get('photo'))})
    return jsonify(records=rows, decisions=load_reviews(), can_edit=_can_review())


@app.post("/api/review")
def review_save():
    if not _can_review():
        return jsonify(error="Review decisions can only be saved on a local copy (python backend/app.py), then committed."), 403
    body = _body()
    rid, state, note = body.get("id"), body.get("state"), body.get("note") or ""
    if not isinstance(rid, str) or not isinstance(note, str) or len(note) > 500 or state not in REVIEW_STATES | {"clear"}:
        return jsonify(error="Send an id, a state (verified, flagged, hidden or clear) and an optional note."), 400
    if not any(isinstance(r, dict) and r.get('id') == rid for r in load_catalog(include_unverified=True)):
        return jsonify(error="No record has that id."), 404
    with _review_lock:
        try:
            data = json.loads(REVIEW_PATH.read_text())
        except (OSError, ValueError):
            data = {}
        decisions = data.get("decisions") if isinstance(data.get("decisions"), dict) else {}
        if state == "clear":
            decisions.pop(rid, None)
        else:
            decisions[rid] = {"state": state, "note": note.strip(), "on": date.today().isoformat()}
        data = {"about": "Team decisions from the /review page. hidden = kept out of every answer and list.",
                "decisions": dict(sorted(decisions.items()))}
        tmp = REVIEW_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        tmp.replace(REVIEW_PATH)
    return jsonify(ok=True, decisions=load_reviews())


@app.get("/api/places")
def places():
    """Northern Virginia place names and the jurisdiction each belongs to, for the map."""
    return jsonify(places=AREAS)


def _body():
    """The JSON request body as a dict; anything else (a list, a number, bad JSON) counts as empty."""
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def _text(body, key, limit=None):
    value = body.get(key)
    return value.strip()[:limit] if isinstance(value, str) else ""


def _gemma_error(error, fallback="Something went wrong. Please try again, or call 211 for help."):
    reason = gemma_unavailable(error)
    return jsonify(error=f"{reason}. Please try again in a few minutes, or call 211 for help." if reason else fallback), (503 if reason else 500)


@app.post("/api/options")
@limited("form")
def find_options():
    """Instant matches for the find form (no AI): listings, programs, and shelters when it's urgent."""
    body = _body()
    fields = {}  # field -> what to fix: a value that was sent but isn't valid is reported, never read as "no limit"

    def number(key, problem, whole=False, low=0, high=10_000_000):
        """A number from the form, or None when it was left blank."""
        raw = body.get(key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return None
        try:
            value = None if isinstance(raw, bool) else float(raw)  # true/false aren't numbers here
        except (TypeError, ValueError, OverflowError):
            value = None
        if value is None or not math.isfinite(value) or not low <= value <= high or (whole and not value.is_integer()):
            fields[key] = problem
            return None
        return int(value) if whole else value

    def text(key, limit):
        raw = body.get(key)
        if raw is not None and not isinstance(raw, str):
            fields[key] = f"{key} must be text."
        return raw[:limit] if isinstance(raw, str) else ""

    profile = {"location": text("location", 100), "budget": number("budget", "Enter a monthly budget from $0 to $100,000, or leave it blank.", high=100_000),
               "bedrooms": number("bedrooms", "Bedrooms must be a whole number from 0 (studio) to 6.", True, 0, 6),
               "accessible": body.get("accessible") is True, "senior": body.get("senior") is True, "tonight": body.get("tonight") is True,
               "voucher": body.get("voucher") is True, "income": number("income", "Enter a yearly income from $0 to $10,000,000, or leave it blank."),
               "household": number("household", "Household size must be a whole number from 1 to 20.", True, 1, 20),
               "situation": redact(text("situation", 1700))[0]}
    space = body.get("rental_space")
    if isinstance(space, str) and space in ("room", "entire_home"):
        profile["rental_space"] = space
    elif space not in (None, "", "all"):
        fields["rental_space"] = "rental_space must be all, room or entire_home."
    if fields:
        return jsonify(error=" ".join(dict.fromkeys(fields.values())), fields=fields), 400
    result = options(profile)
    return jsonify(result), (400 if "error" in result else 200)


@app.post("/api/listings/sort")
@limited("sort")
def sort_listings():
    """The mini Gemma chat above the listings: which of the communities on screen fit best, plus a few lines why."""
    body = _body()
    question, ids = _text(body, "question", 300), body.get("ids")
    if not question:
        return jsonify(error="Tell Gemma what matters most, like \"cheapest rooms near Virginia Tech first\"."), 400
    if not isinstance(ids, list) or not ids or len(ids) > 600 or not all(isinstance(i, str) and len(i) < 200 for i in ids):
        return jsonify(error="ids must be the list of communities on screen."), 400
    return jsonify(sorter.sort(expand_nicknames(redact(question)[0]), ids))


@app.post("/api/programs/sort")
@limited("sort")
def sort_programs():
    """The mini Gemma chat on the Resources page: which programs on screen fit best. quick=true answers at once from the
    words; the second call has Gemma order them and say why."""
    body = _body()
    question, ids = _text(body, "question", 300), body.get("ids")
    if not question:
        return jsonify(error="Tell Gemma what help you need, like \"help paying rent in Arlington\"."), 400
    if not isinstance(ids, list) or not ids or len(ids) > 300 or not all(isinstance(i, str) and len(i) < 200 for i in ids):
        return jsonify(error="ids must be the list of programs on screen."), 400
    return jsonify(sorter.sort_programs(expand_nicknames(redact(question)[0]), ids, quick=body.get("quick") is True))


@app.post("/api/hotels")
@limited("places")
def hotels_nearby():
    """Hotels and motels near a place from Google Places, cheapest first, for someone who needs a room tonight (no AI)."""
    found = hotels.near(_text(_body(), "place", 100))
    if found is None:
        return jsonify(error="Clear Home covers Northern Virginia and Blacksburg, VA. Try Blacksburg, Reston, or Woodbridge."), 400
    return jsonify(found)


@app.get("/api/maps-config")
def maps_config():
    """The browser Maps key (restricted to this site's addresses), or null so the page uses its fallback."""
    return jsonify(browser_key=os.environ.get("GOOGLE_MAPS_BROWSER_API_KEY") or None)


@app.post("/api/housing/search")
@limited("places")
def housing_walk_search():
    """Reviewed affordable homes near a supermarket, pharmacy or transit stop, with real walking times."""
    body = _body()
    prompt = redact(str(body.get("prompt") or "")[:500])[0]
    raw = body.get("filters") if isinstance(body.get("filters"), dict) else {}
    overrides, fields = {}, {}
    # A choice that was sent but isn't one of the allowed values is reported (400), not ignored or crashed on.
    for key, allowed in (("requiredAmenity", tuple(walkable.AMENITIES)), ("maxWalkingMinutes", (5, 10, 15, 20)), ("sort", ("best", "rent", "walk"))):
        value = raw.get(key)
        if value is not None and not (type(value) in (str, int) and value in allowed):
            fields[key] = f"{key} must be one of: {', '.join(map(str, allowed))}."
    if raw.get("bedrooms") is not None and not (type(raw["bedrooms"]) is int and 0 <= raw["bedrooms"] <= 6):
        fields["bedrooms"] = "bedrooms must be a whole number from 0 to 6."
    rent = raw.get("maxMonthlyRent")
    if rent is not None and not (type(rent) in (int, float) and math.isfinite(rent) and 0 < rent < 100_000):
        fields["maxMonthlyRent"] = "maxMonthlyRent must be a number above 0 and under 100,000."
    if fields:
        return jsonify(error=" ".join(fields.values()), fields=fields), 400
    if isinstance(raw.get("location"), str) and raw["location"].strip():
        overrides["location"] = raw["location"].strip()[:100]
    if isinstance(raw.get("maxMonthlyRent"), (int, float)) and 0 < raw["maxMonthlyRent"] < 100_000:
        overrides["max_rent"] = float(raw["maxMonthlyRent"])
    if raw.get("requiredAmenity") is not None:
        overrides["amenity"] = raw["requiredAmenity"]
    if raw.get("maxWalkingMinutes") is not None:
        overrides["max_walk_minutes"] = raw["maxWalkingMinutes"]
    if isinstance(raw.get("strict"), bool):
        overrides["strict"] = raw["strict"]
    if raw.get("sort") is not None:
        overrides["sort"] = raw["sort"]
    if isinstance(raw.get("bedrooms"), int) and 0 <= raw["bedrooms"] <= 6:
        overrides["bedrooms"] = raw["bedrooms"]
    if raw.get("senior") is True:
        overrides["senior"] = True
    if not prompt and not overrides:
        return jsonify(error="Describe what you're looking for, or pick some filters."), 400
    result = walkable.search(prompt, overrides)
    return jsonify(result), (400 if "error" in result else 200)


@app.post("/api/housing/route")
@limited("places")
def housing_walk_route():
    """Walking route line from a verified home to a place an earlier search returned."""
    body = _body()
    home = next((r for r in load_catalog() if r.get("id") == body.get("housing_id")), None)
    if not home or home.get("lat") is None or not isinstance(body.get("place_id"), str):
        return jsonify(error="Route unavailable."), 404
    try:
        route = walkable.walking_route(home["lat"], home["lon"], body["place_id"])
    except Exception:
        route = None
    return (jsonify(route), 200) if route else (jsonify(error="Walking route unavailable."), 404)


@app.get("/api/place-photo")
@limited("photos")
def place_photo():
    """Google place photo, fetched server-side so the server key never reaches the browser."""
    try:
        found = walkable.place_photo(request.args.get("name", ""))
    except Exception:
        found = None
    if not found:
        return jsonify(error="Photo unavailable."), 404
    data, mimetype = found
    return app.response_class(data, mimetype=mimetype, headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/boundaries")
def boundaries():
    """Outlines of the nine Northern Virginia jurisdictions (US Census TIGERweb), for the map."""
    return send_from_directory(os.path.join(FRONTEND, "..", "data"), "nova_boundaries.geojson", mimetype="application/geo+json")


@app.post("/api/live-search")
@limited("web")
def web_search():
    """Gemma searches the web for affordable listings in a typed location. Results are labeled unreviewed."""
    location = str((_body()).get("location", "")).strip()[:100]
    if len(location) < 3:
        return jsonify(error="Type Blacksburg or a Northern Virginia city or county."), 400
    location, _ = redact(location)
    try:
        result = live_search(location, queue_results=not READ_ONLY)
    except Exception as error:
        reason = gemma_unavailable(error)  # a missing key or billing problem won't fix itself on a retry
        return jsonify(error=f"{reason}, so the web search can't run. The reviewed listings still work." if reason else "The web search didn't work this time. Please try again."), (503 if reason else 502)
    return jsonify(result), (400 if "error" in result else 200)


@app.get("/api/programs")
def list_programs():
    """Verified vouchers, rent help, legal aid and other services, without an AI call."""
    return jsonify(programs=programs())


def _chat_request():
    """Shared checks for both chat routes: (question, history, instant answer or None), or an error response."""
    body = _body()
    question = _text(body, "question")
    if not question:
        return None, None, (jsonify(error="Please type a question."), 400)
    if len(question) > 1500:
        return None, None, (jsonify(error="Please keep your question under 1,500 characters."), 400)
    question = expand_nicknames(redact(question)[0])  # "vtech", "gmu": the campus written out for every step below
    # Suicide, self-harm or abuse at home: the hotline first, before any other step (plus the area's own line when it's known).
    form_place = body.get("profile", {}).get("location") if isinstance(body.get("profile"), dict) else None
    lifeline = crisis.answer(question, redact(form_place[:100])[0] if isinstance(form_place, str) else None)
    history = []
    for turn in (body.get("history") if isinstance(body.get("history"), list) else [])[-4:]:
        if isinstance(turn, dict) and turn.get("role") in ("user", "assistant") and isinstance(turn.get("text"), str):
            history.append({"role": turn["role"], "text": expand_nicknames(redact(turn["text"][:2000])[0])})
    # Choices from the find form, so the assistant can tailor its answer (no names or IDs are collected).
    profile = body.get("profile") if isinstance(body.get("profile"), dict) else {}
    # The /app chat sends this conversation's answers to its follow-up questions (kept by the page, checked here): a vague
    # request gets one question with answer buttons first, and the answers are written into the request.
    chat, asking = (clarifier.load_state(body.get("chat")), None) if "chat" in body else (None, None)
    # Finding or avoiding places by who lives there: a fair-housing answer first, before any follow-up question.
    # Questions about Clear Home itself, "thanks"/"bye", a role to play or a notice to write: answered before any follow-up question.
    fair = None if lifeline else (fair_housing_answer(question) or boundary_answer(question) or about_answer(question)
                                  or social_answer(question, history, pending=bool(chat and chat.get("pending"))))
    if chat is not None and not fair:
        question = clarifier.reply_in_words(question, chat, history)  # a reply to near_place.py's "Which Walmart, or which city?"
        try:
            asking, question = clarifier.resolve(question, chat, profile, body.get("reply"))
        except clarifier.Stale as error:
            return None, None, (jsonify(error=str(error)), 409)
        except ValueError as error:
            return None, None, (jsonify(error=str(error)), 400)
        g.chat, g.chat_question = chat, question
    else:
        question = with_context(question, history)  # a reply to the chat's own follow-up question keeps the earlier request
    about = []
    real = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)  # true/false and Infinity aren't numbers here
    # An area or budget answered in the chat is newer than the find form's, so the form's isn't repeated.
    if isinstance(profile.get("location"), str) and profile["location"].strip() and not clarifier.known(chat, "area"): about.append(f"looking in {redact(profile['location'][:100])[0]}")
    for key, label in (("budget", "monthly budget ${:,.0f}"), ("income", "household income ${:,.0f} a year")):
        if real(profile.get(key)) and 0 < profile[key] < 10_000_000 and not (key == "budget" and clarifier.known(chat, "budget")): about.append(label.format(profile[key]))
    if real(profile.get("household")) and 1 <= profile["household"] <= 20: about.append(f"{int(profile['household'])} people in the home")
    if real(profile.get("bedrooms")) and 0 <= profile["bedrooms"] <= 6 and float(profile["bedrooms"]).is_integer(): profile["bedrooms"] = int(profile["bedrooms"]); about.append("studio" if profile["bedrooms"] == 0 else f"{profile['bedrooms']} bedrooms")
    if profile.get("timing") in ("now", "soon", "planning"): about.append({"now": "needs to move as soon as possible", "soon": "moving in the next 3 months", "planning": "planning ahead"}[profile["timing"]])
    for key, label in (("tonight", "needs a safe place tonight"), ("accessible", "needs an accessible home"), ("senior", "someone is 62 or older"), ("voucher", "already has a housing voucher")):
        if profile.get(key) is True: about.append(label)
    # A rental search near "campus" without saying which: ask first, repeating what was understood (no AI).
    # "Close to walmart": which store (asked when no town is known), then only homes a measured walk away (near_place.py).
    # "Near my office at 1800 Tysons Blvd", "near Inova Fairfax Hospital": geocoded and ranked by distance, no AI.
    # These shortcuts read the person's own words, not the profile note added below.
    # A place we don't cover (Richmond, Maryland...): said plainly, with 211, instead of homes from elsewhere.
    instant = lifeline or fair or (asking or outside_answer(question) or named_answer(question) or (None if chat is not None else clarify(question, profile)) or near_place.answer(question, profile, history)
               or nearby.answer(question, profile, history) or quick_nearby(question, profile))  # "near George Mason" etc.: catalog, no AI
    if chat is not None and isinstance(instant, clarifier.Question) and not asking:
        clarifier.record(chat, instant)  # near_place.py or nearby.py asked ("which Walmart?"): that's the open question now
    if about:
        question = f"{question}\n\n(About me: {'; '.join(about)}.)"
    return question, history, instant


@app.post("/api/ask")
@limited("chat")
def ask_advisor():
    question, history, instant = _chat_request()
    if question is None:
        return instant
    chat = {"chat": g.chat} if "chat" in g else {}
    if instant:
        return jsonify(answer=instant, **chat, **({"question": instant.question} if isinstance(instant, clarifier.Question) else {}),
                       **({"lines": instant.lines} if getattr(instant, "lines", None) else {}))
    try:
        return jsonify(answer=ask(question, history), **chat)
    except Exception as error:
        # Same fallback as the streaming chat: the verified resources that match, instead of an error box.
        import advisor
        reason = gemma_unavailable(error) or "The AI service didn't answer"
        return jsonify(answer=advisor.fallback_answer(advisor._records(question, history)[:5], reason, question), **chat)


@app.post("/api/gemma/warm")
@limited("warm")
def warm_gemma():
    """Pages call this when someone presses Get Started or the chat comes into view, so our Gemma GPU (which sleeps
    when idle) wakes up before the first question."""
    import gemma_gpu
    woke = gemma_gpu.warm()
    return jsonify(ok=True, gpu=bool(gemma_gpu.url()), waking=woke)


@app.post("/api/ask/stream")
@limited("chat")
def ask_advisor_stream():
    """The chat with live updates (server-sent events): what was found, then Gemma's answer as it's written."""
    question, history, instant = _chat_request()
    if question is None:
        return instant
    # Somewhere to stay tonight: hotels and motels nearby are looked up while Gemma writes, and sent after its answer.
    # Not while the chat is still asking where: no results from a guessed place.
    body, chat, asking = _body(), g.get("chat"), isinstance(instant, clarifier.Question)
    place = None if asking else hotels.place_for(g.get("chat_question") or redact(_text(body, "question"))[0], body.get("profile") if isinstance(body.get("profile"), dict) else {})
    rooms = hotels.lookup_later(place) if place else None
    advice = not asking and advice_question(g.get("chat_question") or question)

    def hotels_event():
        try:
            found = rooms.result(timeout=10) if rooms else None
        except Exception:
            found = None
        return f"data: {json.dumps({'kind': 'hotels', 'text': found})}\n\n" if found else ""

    def events():
        engine = getattr(instant, "engine", "Instant answer from our verified list with Google Maps Platform (Places + Routes); no AI needed")
        # A question goes as its words (for the transcript) plus its answer choices as data; no cards or map moves yet.
        updates = ([("engine", engine), ("answer", instant)] + ([("question", instant.question)] if asking else [("cards", cards_for(instant))])
                   + ([("lines", instant.lines)] if getattr(instant, "lines", None) else [])  # crisis answers: call and text buttons
                   + ([("suggest", list(instant.suggest))] if getattr(instant, "suggest", None) else [])  # no match: one-tap next searches
                   if instant else stream_ask(question, history))
        sent = False
        if chat is not None:  # the conversation's answers, for the page to send back with the next message
            yield f"data: {json.dumps({'kind': 'state', 'text': chat})}\n\n"
        try:
            for kind, text in updates:
                if kind == "done":  # hotels go just before the end
                    sent = True
                    yield hotels_event()
                if kind == "cards" and advice:  # advice, not a search: the page keeps the cards behind a button
                    yield f"data: {json.dumps({'kind': 'advice', 'text': True})}\n\n"
                yield f"data: {json.dumps({'kind': kind, 'text': text})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'kind': 'fallback', 'text': 'Something went wrong. Please try again, or call 211 for help.'})}\n\n"
        if not sent:
            yield hotels_event()  # answers that end without "done" (instant, fallback)
    return Response(stream_with_context(events()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/match")
@limited("chat")
def match():
    message = _text(_body(), "message")
    if not message:
        return jsonify(error="Please describe your situation."), 400
    if len(message) > 2000:
        return jsonify(error="Please keep it under 2000 characters."), 400
    message, _ = redact(message)
    if not READ_ONLY:  # hosted copies can't keep file changes, so these only run locally
        refresh_in_background()  # queue new open-data records for team review; no-op if refreshed today
        check_in_background()  # take down listings whose provider page no longer offers them
    try:
        filters, answer = find_help(message, include_unverified=bool(os.getenv("INCLUDE_UNVERIFIED")))
    except Exception as error:
        return _gemma_error(error)
    return jsonify(filters=filters, answer=answer)


# Under gunicorn (the hosted server) this module is imported once per worker, so warm up here.
if os.environ.get("WARM_EXAMPLES") == "1":
    warm_examples()


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":  # only in the reloader's serving process, not twice
        warm_examples()
    app.run(port=8000, debug=True)
