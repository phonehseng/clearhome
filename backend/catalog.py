"""Canonical JSON housing catalog: validation and deterministic matching.

Run: python backend/catalog.py --check
No network or AI calls are made by this module.
"""
import argparse
import copy
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

RESOURCES_PATH = Path(__file__).resolve().parent.parent / 'data' / 'resources.json'
STATUSES = {'available_now', 'advertised_vacancy', 'upcoming', 'leasing', 'waitlist_open', 'contact_for_availability', 'closed'}
# affordable_property: an income-restricted building from a public database, without unit-level availability.
TYPES = {'affordable_listing', 'affordable_property', 'emergency_shelter', 'rental_assistance', 'housing_authority', 'legal_aid', 'food_support', 'other'}
STATUS_ORDER = {key: i for i, key in enumerate(['available_now', 'advertised_vacancy', 'upcoming', 'leasing', 'waitlist_open', 'contact_for_availability', 'needs_recheck', 'closed'])}

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

def validate_resources(records):
    """Return actionable data errors; never modify records or mark them verified."""
    if not isinstance(records, list):
        return ['Catalog must be a JSON array.']
    errors, seen = [], set()
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
        if not _https(row.get('source_url')) or not _date(row.get('last_verified')):
            errors.append(f'{label}: verified resources need an HTTPS source and review date.')
        if any(word in str(row).upper() for word in ('PLACEHOLDER', 'REPLACE WITH')):
            errors.append(f'{label}: placeholder text is not allowed in verified records.')
        if row.get('accessible') is not None and type(row['accessible']) is not bool:
            errors.append(f'{label}: accessible must be true, false, or null.')
        if row.get('monthly_rent') is not None and not _number(row['monthly_rent']):
            errors.append(f'{label}: monthly_rent must be a nonnegative number or null.')
        for field in ('bedrooms', 'minimum_age'):
            if row.get(field) is not None and (type(row[field]) is not int or row[field] < 0):
                errors.append(f'{label}: {field} must be a nonnegative integer or null.')
        if row.get('type') != 'affordable_listing':
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

def load_catalog(path=None, include_unverified=False):
    rows = json.loads(Path(path or RESOURCES_PATH).read_text())
    if include_unverified:
        return rows
    # Reject invalid data individually so a malformed entry cannot become a recommendation.
    return [r for r in rows if isinstance(r, dict) and r.get('verified') is True and not validate_resources([r])]

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
        row = copy.deepcopy(resource)
        if row.get('availability') is not None:
            row['availability'] = effective_availability(row, today)
            if row['availability'].get('status') in {'closed', 'needs_recheck'}:
                continue
        if filters.get('urgency') == 'emergency' and row.get('availability', {}).get('status') in {'waitlist_open', 'upcoming', 'leasing', 'contact_for_availability'}:
            continue
        if filters.get('types') and row.get('type') not in filters['types']:
            continue
        if filters.get('needs_accessible') and row.get('accessible') is not True:
            continue
        if row.get('type') == 'affordable_listing':
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
            searchable = ' '.join(str(row.get(k) or '') for k in ('city', 'jurisdiction', 'area', 'address', 'region')).casefold()
            regional = row.get('jurisdiction') == 'Northern Virginia'  # e.g. legal aid and 211 serve the whole region
            if not regional and not any(str(location).casefold() in searchable or str(location).casefold() in {'nova', 'northern va'} for location in locations):
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
