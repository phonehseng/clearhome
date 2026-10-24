"""Small web server: serves the page in frontend/ and the /api endpoints.

Run:  python backend/app.py      then open http://localhost:8000 (about page) or /app (tools)
Set INCLUDE_UNVERIFIED=1 to also use placeholder entries while testing.
"""
import json
import os
import math

from flask import Flask, Response, jsonify, request, send_from_directory, send_file, stream_with_context

from advisor import AREAS, ask, cards_for, options, programs, quick_nearby, stream_ask, warm_examples
from live_search import search as live_search
import nearby
import walkable
from matcher import gemma_unavailable, find_help
from catalog import filter_catalog, group_listings, load_catalog, STATUSES
from listing_photos import cached_photo, photo_mimetype, PhotoUnavailable
from redact import redact
from sources import refresh_in_background
from freshness import check_in_background

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
# Cloud Run's disk resets on every restart, so the hosted copy never writes data files.
READ_ONLY = os.environ.get("CLEARHOUSE_READ_ONLY") == "1"
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # requests are small JSON; no uploads


@app.get("/logo.svg")
def logo():
    return send_from_directory(FRONTEND, "logo.svg")


@app.get("/favicon.svg")
@app.get("/favicon.ico")
@app.get("/apple-touch-icon.png")
def site_icon():
    """The Clear House logo as the browser-tab and home-screen icon."""
    name = request.path.lstrip("/")
    return send_from_directory(FRONTEND, name, max_age=86400)


@app.get("/")
def about():
    return send_from_directory(FRONTEND, "about.html")


@app.get("/app")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get('/listing-map.js')
def listing_map_js():
    return send_from_directory(FRONTEND, 'listing-map.js')


@app.get('/rental-labels.js')
def rental_labels():
    return send_from_directory(FRONTEND, 'rental-labels.js')


@app.get("/media/listings/<resource_id>")
def listing_photo(resource_id):
    # IDs resolve to trusted catalog metadata; arbitrary URLs are never accepted.
    row = next((row for row in load_catalog() if row.get('id') == resource_id), None)
    if not row or not row.get('photo'):
        return jsonify(error="No provider photo is available for this listing."), 404
    try:
        path = cached_photo(row['photo'])
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
    if grouping == 'community':
        rows = group_listings(rows, sort=sort)
    elif sort == 'rent_asc':
        rows.sort(key=lambda row: (row.get('monthly_rent') is None, row.get('monthly_rent') or 0))
    return jsonify(listings=rows, count=len(rows), option_count=option_count, notice="Official-source web review, not a live vacancy feed. Confirm rent, eligibility and availability directly. Closed or overdue records are excluded.")


@app.get("/resources")
def resources_page():
    return send_from_directory(FRONTEND, "resources.html")


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
def find_options():
    """Instant matches for the find form (no AI): listings, programs, and shelters when it's urgent."""
    body = _body()
    def number(key, kind=float, low=0, high=10_000_000):
        raw = body.get(key)
        if isinstance(raw, bool):  # true/false aren't numbers here
            return None
        try:
            value = kind(raw)
            return value if math.isfinite(value) and low <= value <= high else None
        except (TypeError, ValueError, OverflowError):
            return None
    profile = {"location": str(body.get("location") or "")[:100], "budget": number("budget"), "bedrooms": number("bedrooms", int, 0, 6),
               "accessible": body.get("accessible") is True, "senior": body.get("senior") is True, "tonight": body.get("tonight") is True,
               "voucher": body.get("voucher") is True, "income": number("income"), "household": number("household", int, 1, 20),
               "situation": redact(str(body.get("situation") or "")[:1700])[0]}
    if body.get('rental_space') in {'room', 'entire_home'}:
        profile['rental_space'] = body['rental_space']
    result = options(profile)
    return jsonify(result), (400 if "error" in result else 200)


@app.get("/api/maps-config")
def maps_config():
    """The browser Maps key (restricted to this site's addresses), or null so the page uses its fallback."""
    return jsonify(browser_key=os.environ.get("GOOGLE_MAPS_BROWSER_API_KEY") or None)


@app.post("/api/housing/search")
def housing_walk_search():
    """Reviewed affordable homes near a supermarket, pharmacy or transit stop, with real walking times."""
    body = _body()
    prompt = redact(str(body.get("prompt") or "")[:500])[0]
    raw = body.get("filters") if isinstance(body.get("filters"), dict) else {}
    overrides = {}
    if isinstance(raw.get("location"), str) and raw["location"].strip():
        overrides["location"] = raw["location"].strip()[:100]
    if isinstance(raw.get("maxMonthlyRent"), (int, float)) and 0 < raw["maxMonthlyRent"] < 100_000:
        overrides["max_rent"] = float(raw["maxMonthlyRent"])
    if raw.get("requiredAmenity") in walkable.AMENITIES:
        overrides["amenity"] = raw["requiredAmenity"]
    if raw.get("maxWalkingMinutes") in (5, 10, 15, 20):
        overrides["max_walk_minutes"] = raw["maxWalkingMinutes"]
    if isinstance(raw.get("strict"), bool):
        overrides["strict"] = raw["strict"]
    if raw.get("sort") in ("best", "rent", "walk"):
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
def housing_walk_route():
    """Walking route line from a reviewed home to a place an earlier search returned."""
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
def web_search():
    """Gemma searches the web for affordable listings in a typed location. Results are labeled unreviewed."""
    location = str((_body()).get("location", "")).strip()[:100]
    if len(location) < 3:
        return jsonify(error="Type Blacksburg or a Northern Virginia city or county."), 400
    location, _ = redact(location)
    try:
        result = live_search(location, queue_results=not READ_ONLY)
    except Exception:
        return jsonify(error="The web search didn't work this time. Please try again."), 502
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
    question, _ = redact(question)
    history = []
    for turn in (body.get("history") if isinstance(body.get("history"), list) else [])[-4:]:
        if isinstance(turn, dict) and turn.get("role") in ("user", "assistant") and isinstance(turn.get("text"), str):
            history.append({"role": turn["role"], "text": redact(turn["text"][:2000])[0]})
    # Choices from the find form, so the assistant can tailor its answer (no names or IDs are collected).
    profile = body.get("profile") if isinstance(body.get("profile"), dict) else {}
    about = []
    real = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)  # true/false and Infinity aren't numbers here
    if isinstance(profile.get("location"), str) and profile["location"].strip(): about.append(f"looking in {redact(profile['location'][:100])[0]}")
    for key, label in (("budget", "monthly budget ${:,.0f}"), ("income", "household income ${:,.0f} a year")):
        if real(profile.get(key)) and 0 < profile[key] < 10_000_000: about.append(label.format(profile[key]))
    if real(profile.get("household")) and 1 <= profile["household"] <= 20: about.append(f"{int(profile['household'])} people in the home")
    if real(profile.get("bedrooms")) and 0 <= profile["bedrooms"] <= 6 and float(profile["bedrooms"]).is_integer(): profile["bedrooms"] = int(profile["bedrooms"]); about.append("studio" if profile["bedrooms"] == 0 else f"{profile['bedrooms']} bedrooms")
    if profile.get("timing") in ("now", "soon", "planning"): about.append({"now": "needs to move as soon as possible", "soon": "moving in the next 3 months", "planning": "planning ahead"}[profile["timing"]])
    for key, label in (("tonight", "needs a safe place tonight"), ("accessible", "needs an accessible home"), ("senior", "someone is 62 or older"), ("voucher", "already has a housing voucher")):
        if profile.get(key) is True: about.append(label)
    # "Near my office at 1800 Tysons Blvd", "near Inova Fairfax Hospital": geocoded and ranked by distance, no AI.
    # Both shortcuts read the person's own words, not the profile note added below.
    instant = nearby.answer(question, profile) or quick_nearby(question, profile)  # "near George Mason" etc.: catalog, no AI
    if about:
        question = f"{question}\n\n(About me: {'; '.join(about)}.)"
    return question, history, instant


@app.post("/api/ask")
def ask_advisor():
    question, history, instant = _chat_request()
    if question is None:
        return instant
    if instant:
        return jsonify(answer=instant)
    try:
        return jsonify(answer=ask(question, history))
    except Exception as error:
        return _gemma_error(error)


@app.post("/api/gemma/warm")
def warm_gemma():
    """The page calls this when the chat comes into view, so our Gemma GPU (which sleeps when idle) wakes up."""
    import gemma_gpu
    gemma_gpu.warm()
    return jsonify(ok=True, gpu=bool(gemma_gpu.url()))


@app.post("/api/ask/stream")
def ask_advisor_stream():
    """The chat with live updates (server-sent events): what was found, then Gemma's answer as it's written."""
    question, history, instant = _chat_request()
    if question is None:
        return instant

    def events():
        engine = "Instant answer from our checked list with Google Maps Platform (Places + Routes); no AI needed"
        updates = [("engine", engine), ("answer", instant), ("cards", cards_for(instant))] if instant else stream_ask(question, history)
        try:
            for kind, text in updates:
                yield f"data: {json.dumps({'kind': kind, 'text': text})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'kind': 'fallback', 'text': 'Something went wrong. Please try again, or call 211 for help.'})}\n\n"
    return Response(stream_with_context(events()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/match")
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
    except Exception:
        return jsonify(error="Something went wrong. Please try again, or call 211 for help."), 500
    return jsonify(filters=filters, answer=answer)


# Under gunicorn (the hosted server) this module is imported once per worker, so warm up here.
if os.environ.get("WARM_EXAMPLES") == "1":
    warm_examples()


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":  # only in the reloader's serving process, not twice
        warm_examples()
    app.run(port=8000, debug=True)
