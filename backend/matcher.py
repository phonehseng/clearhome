"""Match a person's situation to verified housing resources using Gemma 4.

Usage:
    python backend/matcher.py "I have two kids, $900 a month, need a wheelchair-accessible place"
    python backend/matcher.py --include-unverified "..."   # also use placeholder entries (testing only)
"""
import json
import os
import re
import sys
import time

from dotenv import load_dotenv
from google import genai

ROOT = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(ROOT, ".env"))

MODEL = "gemma-4-26b-a4b-it"
RESOURCES_PATH = os.path.join(ROOT, "data", "resources.json")
TYPES = [
    "rental_listing",
    "emergency_shelter",
    "rental_assistance",
    "legal_aid",
    "affordable_listing",
    "affordable_property",
    "food_support",
    "housing_authority",
    "other",
]

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.startswith("AIza...") or api_key == "your-key-here":
            raise SystemExit("Set GEMINI_API_KEY in the .env file at the project root.")
        _client = genai.Client(api_key=api_key)
    return _client


def ask_gemma(prompt, attempts=3):
    """Call Gemma, retrying on temporary server errors."""
    for attempt in range(attempts):
        try:
            return _get_client().models.generate_content(model=MODEL, contents=prompt).text
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))


def load_resources(include_unverified=False):
    with open(RESOURCES_PATH) as f:
        resources = json.load(f)
    if include_unverified:
        return resources
    return [r for r in resources if r.get("verified")]


def extract_filters(message):
    """Turn free text into structured filters. Falls back to no filters if parsing fails."""
    prompt = f"""Extract housing filters from the message below. Return ONLY a JSON object with these keys:
- "types": list of the resource types that fit what the person needs, chosen from {TYPES}
- "max_budget_per_month": number or null
- "needs_accessible": true or false
- "urgency": "emergency" if they have nowhere safe to stay tonight or soon, otherwise "soon" or "planning"

Message: {message}"""
    default = {"types": [], "max_budget_per_month": None, "needs_accessible": False, "urgency": "soon"}
    try:
        text = ask_gemma(prompt)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        parsed = json.loads(match.group(0))
    except Exception:
        return default
    filters = {**default, **{k: v for k, v in parsed.items() if k in default}}
    filters["types"] = [t for t in filters["types"] if t in TYPES]
    return filters


def filter_resources(resources, filters):
    """Pick matching entries. Shelters come first when the situation is urgent."""
    types = filters.get("types") or []
    if "affordable_listing" in types and "affordable_property" not in types:
        # Someone looking for an apartment also wants income-restricted buildings with no advertised vacancy yet.
        filters = {**filters, "types": types + ["affordable_property"]}
    if filters.get("urgency") == "emergency" and "emergency_shelter" in (filters.get("types") or []) and "other" not in filters["types"]:
        # Intake lines and hotlines are filed as "other" but are the way into most shelters.
        filters = {**filters, "types": filters["types"] + ["other"]}
    matches = resources
    if filters["types"]:
        matches = [r for r in matches if r.get("type") in filters["types"]]
    if filters["needs_accessible"]:
        matches = [r for r in matches if r.get("accessible") is not False]
    if filters["urgency"] == "emergency":
        matches = sorted(matches, key=lambda r: r.get("type") != "emergency_shelter")
    return matches


def write_answer(message, filters, matches):
    from prompt_tools import compact
    prompt = f"""You are a housing assistant helping a low-income person. Answer using ONLY the resources listed below.

Rules:
- This service covers Northern Virginia and Blacksburg, Virginia (including student rooms near Virginia Tech). Match the requested region; local Northern Virginia services do not serve Blacksburg unless explicitly recorded.
- Room prices are per person, not whole-apartment prices. State the payment schedule, lease dates, and individual or joint responsibility as recorded. Never turn an estimated roommate split into an advertised room price.
- Recommend only resources from the list. Never invent places, phone numbers, prices or addresses.
- For each recommendation give the name, phone, address, cost, requirements, source_url and availability.checked_on (or last_verified). Say when accessibility is unknown.
- When a resource has how_to_apply, include those steps in short plain language. For shelters, say to call the intake line first, since most beds are assigned through it.
- When a program has waitlist_status, state it plainly. Never say a waitlist is open unless waitlist_status is "open".
- affordable_property entries are income-restricted buildings from a public database with no confirmed vacancy: tell the person to call and ask about openings or the waitlist.
- If nothing in the list fits, say so plainly and suggest calling 211 for local help.
- If the person may be in danger tonight, mention calling 911 for emergencies and 211 for shelter.
- Their budget is {filters['max_budget_per_month']} per month: only suggest listings that fit it, using each entry's cost text.
- Use short, plain language. Say these are suggestions, not legal advice.

Person's message: {message}

Resources:
{json.dumps(compact(matches), ensure_ascii=False)}"""
    return ask_gemma(prompt)


def find_help(message, include_unverified=False):
    resources = load_resources(include_unverified)
    # A keyword script reads most messages instantly; Gemma only parses ones it can't understand.
    from prompt_tools import keyword_filters  # imported here: prompt_tools -> advisor -> matcher
    filters, confident = keyword_filters(message)
    if not confident:
        filters = {**extract_filters(message), 'locations': filters['locations']}
    from catalog import filter_catalog
    resources = filter_catalog(resources, filters)
    matches = filter_resources(resources, filters)
    if not matches:
        return filters, "I don't have a verified match for that yet. Please call 211 (or visit 211virginia.org) for local housing help."
    return filters, write_answer(message, filters, matches)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--include-unverified"]
    include = "--include-unverified" in sys.argv
    if not args:
        raise SystemExit(__doc__)
    filters, answer = find_help(" ".join(args), include)
    print("Filters:", json.dumps(filters))
    print()
    print(answer)
