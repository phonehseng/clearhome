"""Canonical JSON housing catalog: validation and deterministic matching.

Run: python backend/catalog.py --check
No network or AI calls are made by this module.
"""
import argparse
import copy
import json
import math
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

RESOURCES_PATH = Path(__file__).resolve().parent.parent / 'data' / 'resources.json'
# Team decisions from the /review page: verified, flagged (needs a human check) or hidden (kept out of every answer).
REVIEW_PATH = Path(__file__).resolve().parent.parent / 'data' / 'listing_review.json'
REVIEW_STATES = {'verified', 'flagged', 'hidden'}
STATUSES = {'available_now', 'advertised_vacancy', 'upcoming', 'leasing', 'waitlist_open', 'contact_for_availability', 'closed'}
# affordable_property: an income-restricted building from a public database, without unit-level availability.
TYPES = {'rental_listing', 'affordable_listing', 'affordable_property', 'emergency_shelter', 'rental_assistance', 'housing_authority', 'legal_aid', 'food_support', 'other'}
STATUS_ORDER = {key: i for i, key in enumerate(['available_now', 'advertised_vacancy', 'upcoming', 'leasing', 'waitlist_open', 'contact_for_availability', 'needs_recheck', 'closed'])}
HOUSING_TYPES = {'affordable_listing', 'affordable_property', 'rental_listing'}
NOVA_JURISDICTIONS = {'Arlington County', 'Fairfax County', 'Loudoun County', 'Prince William County',
                      'Alexandria City', 'Fairfax City', 'Falls Church City', 'Manassas City', 'Manassas Park City'}


def senior_only(row):
    """Use recorded age rules, not an applicant's age or the property's name."""
    age = row.get('minimum_age')
    if type(age) is int and age >= 55:
        return True
    if row.get('eligibility_group') == 'senior':
        return True
    # Reviewed community records sometimes publish an age restriction without
    # its exact threshold. Senior/disability programs are kept separate.
    return ('age-restricted community' in str(row.get('floor_plan', '')).casefold()
            and 'older adults' in str(row.get('who_it_serves', '')).casefold())


def serves_location(row, location):
    """Match a place or explicit service area without crossing regional boundaries."""
    query = str(location).strip().casefold()
    if query in {'nova', 'northern va', 'northern virginia'}:
        return row.get('region') == 'Northern Virginia' or row.get('jurisdiction') in NOVA_JURISDICTIONS | {'Northern Virginia'}
    areas = row.get('service_areas') or []
    if not isinstance(areas, list):
        areas = []
    if any(query == str(area).casefold() for area in areas):
        return True
    if row.get('jurisdiction') == 'Northern Virginia':
        return any(query in area.casefold() for area in NOVA_JURISDICTIONS)
    searchable = ' '.join(str(row.get(k) or '') for k in ('city', 'jurisdiction', 'area', 'address', 'region')).casefold()
    return bool(query) and query in searchable


def _normalized(value):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', '' if value is None else str(value)).casefold()))


def community_key(row):
    """Group physical communities, keeping separate programs at an agency distinct."""
    if row.get('type') not in HOUSING_TYPES:
        return ('resource', row.get('id'))
    street = re.sub(r'\([^)]*\)', '', str(row.get('address') or '').split(',')[0])
    words = _normalized(street).split()
    abbreviations = {'road': 'rd', 'street': 'st', 'avenue': 'ave', 'boulevard': 'blvd',
                     'drive': 'dr', 'court': 'ct', 'lane': 'ln', 'south': 's', 'north': 'n',
                     'east': 'e', 'west': 'w', 'terrace': 'ter', 'place': 'pl'}
    address = ' '.join(abbreviations.get(word, word) for word in words)
    # A street without a building number must not merge unrelated properties.
    name = '' if words and words[0].isdigit() else _normalized(row.get('community') or row.get('name') or row.get('id'))
    return ('community', _normalized(row.get('jurisdiction') or row.get('city')), address, name)


def listing_key(row):
    if row.get('type') not in HOUSING_TYPES:
        return ('resource', row.get('id'))
    category = row.get('affordability') if isinstance(row.get('affordability'), dict) else {}
    unit = str(row.get('unit_number') or row.get('id')) if row.get('record_kind') == 'unit' else None
    return (community_key(row), row.get('type'), _normalized(row.get('floor_plan')),
            str(row.get('bedrooms')), str(row.get('bathrooms')), str(row.get('record_kind')),
            _normalized(category.get('program')), row.get('rental_space', 'entire_home'),
            unit)


def deduplicate_listings(rows):
    """Prefer the latest review of an identical option, including newer closures.

    Price and status are not identity fields: a changed price or closed record
    must replace the older snapshot instead of creating another recommendation.
    """
    unique = {}
    def rank(row):
        availability = row.get('availability') or {}
        return (_date(availability.get('checked_on')) or _date(row.get('last_verified')) or date.min,
                availability.get('status') == 'closed', _date(row.get('last_verified')) or date.min)
    for row in rows:
        key = listing_key(row)
        if key not in unique or rank(row) > rank(unique[key]):
            unique[key] = row
    return list(unique.values())


def group_listings(rows, sort='recommended'):
    """Group only the already-filtered options; never reintroduce excluded plans."""
    grouped = {}
    for row in deduplicate_listings(rows):
        grouped.setdefault(community_key(row), []).append(row)
    cards = []
    def price(row):
        value = row.get('monthly_rent')
        return value if _number(value) else math.inf
    for options in grouped.values():
        options.sort(key=lambda row: (price(row), row.get('floor_plan') or row['name']))
        card = copy.deepcopy(options[0])
        card['floor_plans'] = copy.deepcopy(options)
        cards.append(card)
    if sort == 'rent_asc':
        cards.sort(key=lambda row: (price(row), (row.get('community') or row['name']).casefold()))
    else:
        cards.sort(key=lambda row: min(STATUS_ORDER.get(p.get('availability', {}).get('status'), 5) for p in row['floor_plans']))
    return cards

def _date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None

def _https(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username

def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0

def documented_affordability(row):
    """Evidence is required; a label, low price, or verified flag alone is insufficient."""
    evidence = row.get('affordability')
    return (isinstance(evidence, dict) and evidence.get('status') == 'documented'
            and isinstance(evidence.get('program'), str) and bool(evidence['program'].strip())
            and isinstance(evidence.get('evidence'), str) and bool(evidence['evidence'].strip())
            and _https(evidence.get('source_url')) and _date(evidence.get('checked_on')) is not None)


def documented_rental(row):
    evidence = row.get('affordability')
    return (isinstance(evidence, dict) and evidence.get('status') == 'standard_rental'
            and isinstance(evidence.get('evidence'), str) and bool(evidence['evidence'].strip())
            and _https(evidence.get('source_url')) and _date(evidence.get('checked_on')) is not None)


def validate_resources(records):
    """Return actionable data errors; never modify records or mark them verified."""
    if not isinstance(records, list):
        return ['Catalog must be a JSON array.']
    errors, seen, listings_seen = [], set(), {}
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            errors.append(f'Entry {index}: expected an object.')
            continue
        label = row.get('id', f'entry {index}')
        for field in ('id', 'name', 'type'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f'{label}: missing {field}.')
        if not isinstance(label, str):
            errors.append(f'Entry {index}: id must be a string.')
        elif label in seen:
            errors.append(f'{label}: duplicate id.')
        else:
            seen.add(label)
        if row.get('type') not in TYPES:
            errors.append(f'{label}: unsupported resource type.')
        if row.get('verified') is not True:
            continue  # Drafts may be incomplete but can never be recommended.
        if row.get('type') in HOUSING_TYPES:
            key = listing_key(row)
            if key in listings_seen:
                errors.append(f'{label}: duplicate housing option of {listings_seen[key]}; update the existing record instead.')
            else:
                listings_seen[key] = label
        if not _https(row.get('source_url')) or not _date(row.get('last_verified')):
            errors.append(f'{label}: verified resources need an HTTPS source and review date.')
        if any(word in str(row).upper() for word in ('PLACEHOLDER', 'REPLACE WITH')):
            errors.append(f'{label}: placeholder text is not allowed in verified records.')
        if row.get('accessible') is not None and type(row['accessible']) is not bool:
            errors.append(f'{label}: accessible must be true, false, or null.')
        if row.get('monthly_rent') is not None and not _number(row['monthly_rent']):
            errors.append(f'{label}: monthly_rent must be a nonnegative number or null.')
        if row.get('rental_space') not in (None, 'room', 'entire_home'):
            errors.append(f'{label}: rental_space must be room or entire_home.')
        if row.get('rental_space') == 'room':
            if row.get('bedrooms') != 1 or row.get('price_unit') != 'per_person':
                errors.append(f'{label}: room offers must describe one offered bedroom and per-person pricing.')
            if row.get('lease_type') not in {'individual', 'joint', 'confirm'} or not row.get('lease_responsibility'):
                errors.append(f'{label}: room offers need a lease type and responsibility explanation.')
        for field in ('bedrooms', 'minimum_age'):
            if row.get(field) is not None and (type(row[field]) is not int or row[field] < 0):
                errors.append(f'{label}: {field} must be a nonnegative integer or null.')
        if row.get('type') in {'affordable_listing', 'affordable_property'} and not documented_affordability(row):
            errors.append(f'{label}: housing needs documented affordability evidence, source, program, and review date.')
        if row.get('type') == 'rental_listing' and not documented_rental(row):
            errors.append(f'{label}: regular rentals need provider evidence and a review date.')
        if row.get('type') not in {'affordable_listing', 'rental_listing'}:
            continue
        for field in ('community', 'city', 'jurisdiction', 'address', 'verification_method'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f'{label}: listings need {field}.')
        availability = row.get('availability')
        if not isinstance(availability, dict):
            errors.append(f'{label}: listings need availability evidence.')
            continue
        if availability.get('status') not in STATUSES:
            errors.append(f'{label}: unsupported availability status.')
        checked, due = _date(availability.get('checked_on')), _date(availability.get('review_due'))
        if not checked or not due or due < checked or (due - checked).days > 7:
            errors.append(f'{label}: availability needs checked_on and a review_due within seven days.')
        if availability.get('available_from') is not None and not _date(availability['available_from']):
            errors.append(f'{label}: invalid available_from date.')
        if not availability.get('evidence') or not _https(availability.get('source_url')):
            errors.append(f'{label}: availability needs source evidence.')
    return errors

def load_reviews(path=None):
    """{id: {"state", "note", "on"}} from the review page's file; empty if there is none yet."""
    try:
        data = json.loads(Path(path or REVIEW_PATH).read_text())
    except (OSError, ValueError):
        return {}
    decisions = data.get('decisions') if isinstance(data, dict) else None
    return {k: v for k, v in (decisions or {}).items() if isinstance(v, dict) and v.get('state') in REVIEW_STATES}


_loaded = {}  # validated catalog, kept until the data files change (checking every record takes ~40 ms)


def _mtime(path):
    try:
        return Path(path).stat().st_mtime_ns
    except OSError:
        return None


def load_catalog(path=None, include_unverified=False):
    if include_unverified:
        return json.loads(Path(path or RESOURCES_PATH).read_text())
    stamp = (str(path or RESOURCES_PATH), _mtime(path or RESOURCES_PATH), None if path else _mtime(REVIEW_PATH), date.today())
    if _loaded.get('stamp') != stamp:
        rows = json.loads(Path(path or RESOURCES_PATH).read_text())
        hidden = {k for k, v in load_reviews().items() if v['state'] == 'hidden'} if path is None else set()
        # Reject invalid data individually so a malformed entry cannot become a recommendation.
        _loaded.update(stamp=stamp, rows=deduplicate_listings([r for r in rows if isinstance(r, dict) and r.get('verified') is True
                                                               and r.get('id') not in hidden and not validate_resources([r])]))
    return copy.deepcopy(_loaded['rows'])  # callers may edit their rows

def effective_availability(resource, today=None):
    """Derive staleness without silently changing the reviewed evidence in the file."""
    availability = copy.deepcopy(resource.get('availability') or {})
    today = today or date.today()
    checked, due = _date(availability.get('checked_on')), _date(availability.get('review_due'))
    if availability.get('status') != 'closed' and (not checked or not due or checked > today or due < today):
        availability['status'] = 'needs_recheck'
    return availability

def filter_catalog(resources, filters=None, today=None):
    filters = filters or {}
    results = []
    for resource in resources:
        if resource.get('verified') is not True:
            continue
        if resource.get('type') in {'affordable_listing', 'affordable_property'} and not documented_affordability(resource):
            continue
        if resource.get('type') == 'rental_listing' and not documented_rental(resource):
            continue
        row = copy.deepcopy(resource)
        housing = row.get('type') in HOUSING_TYPES
        if row.get('availability') is not None:
            row['availability'] = effective_availability(row, today)
            if not housing and row['availability'].get('status') == 'needs_recheck':
                # An emergency service whose review lapsed is still worth calling; it just goes back to
                # "call to confirm" instead of disappearing (capacity is never assumed either way).
                row['availability']['status'] = 'contact_for_availability'
            if row['availability'].get('status') in {'closed', 'needs_recheck'}:
                continue
        # In an emergency, homes that are only waitlisted or "call us" aren't a place to stay tonight; shelters and
        # intake lines are, even though their beds are always "call to confirm".
        if housing and filters.get('urgency') == 'emergency' and row.get('availability', {}).get('status') in {'waitlist_open', 'upcoming', 'leasing', 'contact_for_availability'}:
            continue
        if filters.get('types') and row.get('type') not in filters['types']:
            continue
        if filters.get('needs_accessible') and row.get('accessible') is not True:
            continue
        if row.get('type') in {'affordable_listing', 'affordable_property', 'rental_listing'}:
            space = filters.get('rental_space')
            if space in {'room', 'entire_home'} and row.get('rental_space', 'entire_home') != space:
                continue
            group = filters.get('age_group')
            if (group == 'general' and senior_only(row)) or (group == 'senior' and not senior_only(row)):
                continue
            budget = filters.get('max_budget_per_month')
            rent = row.get('monthly_rent')
            if _number(budget) and (not _number(rent) or rent > budget):
                continue
            if filters.get('bedrooms') is not None and row.get('bedrooms') != filters['bedrooms']:
                continue
            age, minimum = filters.get('age'), row.get('minimum_age')
            if type(age) is int and type(minimum) is int and age < minimum:
                continue
            if filters.get('urgency') == 'emergency' and row.get('availability', {}).get('status') != 'available_now':
                continue  # A waitlist or future lease-up cannot solve tonight's housing need.
        locations = filters.get('locations') or []
        if locations:
            if not any(serves_location(row, location) for location in locations):
                continue
        results.append(row)
    return sorted(results, key=lambda r: (0 if r.get('type') == 'emergency_shelter' else 1, STATUS_ORDER.get(r.get('availability', {}).get('status'), 5)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate the canonical resource catalog')
    parser.parse_args()
    rows = json.loads(RESOURCES_PATH.read_text())
    errors = validate_resources(rows)
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'Catalog valid: {len(rows)} records; {len({r.get("community") for r in rows if r.get("type") == "affordable_listing"})} housing communities.')
