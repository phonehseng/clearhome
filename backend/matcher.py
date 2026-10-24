"""Match a person's situation to verified housing resources using Gemma 4.

Usage:
    python backend/matcher.py "I have two kids, $900 a month, need a wheelchair-accessible place"
    python backend/catalog.py --check                    # validate reviewed data offline
"""
import json
import os
import re
import sys
import time

from dotenv import load_dotenv
from google import genai

from catalog import filter_catalog, load_catalog

ROOT = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(ROOT, ".env"))

MODEL = "gemma-4-26b-a4b-it"
RESOURCES_PATH = os.path.join(ROOT, "data", "resources.json")
TYPES = [
    "emergency_shelter",
    "rental_assistance",
    "legal_aid",
    "affordable_listing",
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
    return load_catalog(RESOURCES_PATH, include_unverified=include_unverified)


def extract_filters(message):
    """Normalize model filters; preserve explicit form fields on parse failure."""
    prompt = f"""Extract housing filters from the message below. Return ONLY a JSON object with these keys:
- "types": list of the resource types that fit what the person needs, chosen from {TYPES}
- "max_budget_per_month": number or null
- "needs_accessible": true or false
- "urgency": "emergency" if they have nowhere safe to stay tonight or soon, otherwise "soon" or "planning"
- "locations": list of requested Northern Virginia cities or counties, or an empty list when unspecified
- "bedrooms": requested bedroom count as an integer (0 for studio), or null when unspecified
- "age": the person's explicitly stated age as an integer, otherwise null; never infer age from student status

Message: {message}"""
    default = {"types": [], "max_budget_per_month": None, "needs_accessible": False,
               "urgency": "soon", "locations": [], "bedrooms": None, "age": None}
    try:
        text = ask_gemma(prompt)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception:
        parsed = {}
    filters = {**default, **{k: v for k, v in parsed.items() if k in default}}
    filters["types"] = [t for t in filters["types"] if t in TYPES] if isinstance(filters["types"], list) else []
    filters["locations"] = [v for v in filters["locations"] if isinstance(v, str) and v.strip()] if isinstance(filters["locations"], list) else []
    filters["needs_accessible"] = filters["needs_accessible"] is True
    if not isinstance(filters["urgency"], str) or filters["urgency"] not in {"emergency", "soon", "planning"}:
        filters["urgency"] = "soon"
    for key in ("bedrooms", "age"):
        if type(filters[key]) is not int or filters[key] < 0:
            filters[key] = None
    budget = filters["max_budget_per_month"]
    if type(budget) not in (int, float) or not 0 <= budget < float('inf'):
        filters["max_budget_per_month"] = None
    # Preserve explicit structured frontend fields even if model parsing fails.
    location = re.search(r"^Location: ([^\n]+)\.$", message, re.MULTILINE)
    if location:
        filters["locations"] = [location.group(1)]
    budget = re.search(r"^Maximum monthly budget: \$([0-9]+(?:\.[0-9]+)?)\.$", message, re.MULTILINE)
    if budget:
        filters["max_budget_per_month"] = float(budget.group(1))
    return filters


def filter_resources(resources, filters):
    """Pick matching entries. Shelters come first when the situation is urgent."""
    return filter_catalog(resources, filters)


def write_answer(message, filters, matches):
    prompt = f"""You are a housing assistant helping a low-income person. Answer using ONLY the resources listed below.

Rules:
- This service covers Northern Virginia (Fairfax County, Arlington, Alexandria, Loudoun and Prince William). If the person is clearly looking elsewhere, say so and suggest calling 211.
- Recommend only resources from the list. Never invent places, phone numbers, prices or addresses.
- For each recommendation give the name, phone, address, cost, requirements, source_url and availability.checked_on. Say when accessibility is unknown.
- Availability is a website-advertised snapshot, not a provider-confirmed reservation. Never promise a unit or a place to stay tonight.
- State availability.status plainly: waitlist_open is a waitlist, upcoming is a future date, leasing is general lease-up, contact_for_availability has no confirmed vacancy. Never turn these into an available-now claim.
- Starting rents are potential options only, not a guaranteed total cost. Utilities, fees, income qualification and final rent need confirmation. Do not invent unknown prices.
- Read notes and cost for conflicting prices or temporary specials. Do not present a promotion as the ongoing rent.
- Explain senior age limits and local live/work waitlist requirements where present. Do not assert eligibility without provider confirmation.
- If nothing in the list fits, say so plainly and suggest calling 211 for local help.
- If the person may be in danger tonight, mention calling 911 for emergencies and 211 for shelter.
- Their budget is {filters['max_budget_per_month']} per month: only suggest listings that fit it, using each entry's cost text.
- Use short, plain language. Say these are suggestions, not legal advice.

Person's message: {message}

Resources:
{json.dumps(matches, indent=2)}"""
    return ask_gemma(prompt)


def find_help(message, include_unverified=False):
    resources = load_resources(include_unverified)
    filters = extract_filters(message)
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
