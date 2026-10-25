"""Add one housing listing to data/resources.json by answering questions, so hand-added records are complete.

Run: python backend/add_listing.py            # asks questions, shows the record, saves only after you say yes
     python backend/add_listing.py --dry-run  # same, but never writes anything

The record gets every field the site checks (location, availability, affordability evidence, review dates),
a map pin from the free US Census Geocoder when the address matches, and is validated before saving.
Listings sourced from aggregator sites (Zillow, Apartments.com, ...) are saved unverified and flagged on /review,
because the catalog only shows facts from the property's own site or a public agency.
"""
import argparse
import json
import re
from datetime import date, timedelta
from urllib.parse import urlsplit

from catalog import (NOVA_JURISDICTIONS, RESOURCES_PATH, REVIEW_PATH, STATUSES, community_key, documented_affordability,
                     documented_rental, validate_resources)

LISTING_SITES = ('apartments.com', 'zillow.com', 'trulia.com', 'rent.com', 'hotpads.com', 'redfin.com', 'realtor.com',
                 'apartmentfinder.com', 'apartmentlist.com', 'zumper.com', 'padmapper.com', 'craigslist.org',
                 'facebook.com', 'homefinder.com', 'apartmentguide.com', 'forrent.com', 'rentcafe.com', 'costar.com')
JURISDICTIONS = sorted(NOVA_JURISDICTIONS) + ['Montgomery County']
VERIFIED_METHOD = 'Hand-entered from official provider or public-agency web sources; no phone or in-person confirmation.'
UNVERIFIED_METHOD = ('Hand-entered from listing sites; not yet verified against the property or a public agency. '
                     'Withheld from answers until a teammate confirms it and marks it verified.')


def slug(*parts):
    return re.sub(r'[^a-z0-9]+', '-', ' '.join(p for p in parts if p).casefold()).strip('-')


def listing_site(url):
    host = (urlsplit(url or '').hostname or '').casefold()
    return any(host == d or host.endswith('.' + d) for d in LISTING_SITES)


def phone_format(raw):
    digits = re.sub(r'\D', '', raw or '')
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return f'{digits[:3]}-{digits[3:6]}-{digits[6:]}' if len(digits) == 10 else (raw or '').strip() or None


def location(jurisdiction, city):
    """The region/area convention the filters and map rely on."""
    if jurisdiction == 'Montgomery County':
        return 'New River Valley', city  # Blacksburg and Christiansburg are their own map areas
    return 'Northern Virginia', jurisdiction


def build_record(a, existing_ids=(), today=None):
    """Turn answers (a dict) into a full catalog record. Pure, so it can be tested without prompts."""
    today = today or date.today()
    checked, due = today.isoformat(), (today + timedelta(days=7)).isoformat()
    room = a['space'] == 'room'
    affordable = a['kind'] == 'affordable'
    official = not listing_site(a['source_url'])
    region, area = location(a['jurisdiction'], a['city'])
    rent = a.get('rent')
    plan = a['plan']
    base = slug(a['city'] if region == 'New River Valley' else '', a['community'], plan)
    rid, n = base, 2
    while rid in existing_ids:
        rid, n = f'{base}-{n}', n + 1
    who_pays = 'per person' if room else 'per month for the whole apartment'
    if rent is None:
        cost = 'Rent not published on the reviewed page. Confirm current rent, fees, deposits and utilities with the provider.'
    else:
        cost = (f"{'Provider advertises' if official else 'Listing sites show'} ${rent:,.0f} {who_pays}. "
                'Additional fees, deposits, and utilities may apply; confirm the written total.')
    sources = [{'url': a['source_url'], 'role': 'provider' if official else 'listing_site'}]
    if a.get('website') and a['website'] != a['source_url']:
        sources.append({'url': a['website'], 'role': 'provider'})
    record = {
        'id': rid,
        'name': f"{a['community']} — {plan}",
        'community': a['community'],
        'record_kind': 'unit' if a.get('unit_number') else 'floor_plan',
        'unit_number': a.get('unit_number') or None,
        'floor_plan': plan,
        'type': 'affordable_listing' if affordable else 'rental_listing',
        'address': a['address'],
        'city': a['city'],
        'jurisdiction': a['jurisdiction'],
        'region': region,
        'area': area,
        'state': 'VA',
        'rental_space': 'room' if room else 'entire_home',
        'price_unit': 'per_person' if room else 'per_home',
        'monthly_rent': rent,
        'currency': 'USD',
        'rent_basis': 'not_published' if rent is None else ('per_person_monthly' if room else 'advertised_starting_base'),
        'bedrooms': 1 if room else a.get('bedrooms'),
        'bathrooms': a.get('bathrooms'),
        'square_feet': a.get('square_feet'),
        'shared_home_bedrooms': a.get('shared_bedrooms') if room else None,
        'shared_home_bathrooms': a.get('shared_bathrooms') if room else None,
        'private_bathroom': a.get('private_bathroom') if room else None,
        'student_friendly': bool(a.get('student_friendly')),
        'lease_type': 'confirm',
        'lease_responsibility': (
            'The provider advertises a bedroom in a shared apartment; ask whether the lease is individual or joint '
            'and who owes the full rent.' if room else
            'Whole-apartment lease; ask leasing who owes the full rent if more than one adult signs.'),
        'lease_start': None,
        'lease_end': None,
        'lease_term_notes': a.get('lease_notes') or '',
        'payment_schedule': 'Monthly rent; confirm the lease term and exact charges with leasing.',
        'furnished': None,
        'utilities_notes': a.get('utilities') or '',
        'phone': phone_format(a.get('phone')),
        'website': a.get('website') or None,
        'hours': None,
        'accessible': None,
        'minimum_age': a.get('minimum_age'),
        'accessibility_notes': 'A currently available accessible unit has not been confirmed. Ask about the unit, '
                               'bathroom, entrances, and parking.',
        'who_it_serves': a.get('who') or ('Households that meet the program\'s income limits; eligibility must be confirmed '
                                         'by the provider.' if affordable else
                                         'Applicants meeting the provider\'s rental criteria.'),
        'requirements': 'Confirm the unit, move-in date, total charges, application requirements and lease terms '
                        'directly with the provider.',
        'source_url': a['source_url'],
        'source_kind': 'property_website' if official else 'listing_site',
        'sources': sources,
        'verified': official,
        'last_verified': checked if official else None,
        'verification_method': VERIFIED_METHOD if official else UNVERIFIED_METHOD,
        'catalog_batch': f'hand-added-{checked}',
        'notes': a.get('notes') or 'Website-advertised information is a dated snapshot, not a reservation or guarantee. '
                                   'Confirm directly with the leasing office.',
        'availability': {
            'status': a['status'],
            'checked_on': checked,
            'review_due': due,
            'available_from': a.get('available_from'),
            'source_url': a['source_url'],
            'source_updated_on': None,
            'evidence': a['evidence'],
        },
        'affordability': {
            'status': 'documented' if affordable else 'standard_rental',
            'program': a.get('program') or 'Regular rental; no subsidy claimed',
            'evidence': a.get('program_evidence') or ('The provider publishes this rental option; no income-restricted '
                                                      'designation is assumed from a low price.'),
            'source_url': a.get('program_source') or a['source_url'],
            'checked_on': checked,
            'method': 'Official-source web review; no direct provider confirmation.' if official else
                      'Listing-site review; no provider confirmation.',
            'individual_eligibility_confirmed': False,
        },
        'cost': cost,
        'photo': None,
    }
    if a.get('lat') is not None:
        record.update(lat=a['lat'], lon=a['lon'], geocode_source='US Census Geocoder')
    return record


def problems(record, rows):
    """Errors that would keep the record off the site (checked as if it were verified)."""
    check = dict(record, verified=True, last_verified=record['last_verified'] or record['availability']['checked_on'])
    errors = validate_resources([r for r in rows if r.get('verified') is True] + [check])
    errors = [e for e in errors if e.startswith(record['id'] + ':')]
    shown = documented_affordability(check) if check['type'] == 'affordable_listing' else documented_rental(check)
    return errors + ([] if shown else [f"{record['id']}: missing affordability evidence, so it would be filtered out."])


def similar(record, rows):
    """Records already in the file (verified or not) for the same community, size and room/whole-home type."""
    same = (community_key(record), record['bedrooms'], record['rental_space'])
    return [r['id'] for r in rows if isinstance(r, dict) and r.get('type') in {'affordable_listing', 'rental_listing'}
            and (community_key(r), r.get('bedrooms'), r.get('rental_space', 'entire_home')) == same]


# ---- prompts -------------------------------------------------------------------------------------------------

def ask(question, default=None, required=False, choices=None, kind=str):
    hint = f" [{'/'.join(choices)}]" if choices else ''
    hint += f' (default: {default})' if default not in (None, '') else ''
    while True:
        raw = input(f'{question}{hint}: ').strip()
        if not raw:
            if default is not None or not required:
                return default
            print('  This one is required.')
            continue
        if choices and raw not in choices:
            print(f"  Pick one of: {', '.join(choices)}")
            continue
        try:
            return kind(raw)
        except ValueError:
            print('  That does not look right; try again (numbers like 1550, dates like 2026-11-15).')


def yes(question, default=False):
    return ask(question, 'y' if default else 'n', choices=['y', 'n']) == 'y'


def number(raw):
    """1 -> 1, 2.5 -> 2.5, '$1,550' -> 1550 (whole numbers stay ints, like the rest of the catalog)."""
    value = float(raw.replace('$', '').replace(',', ''))
    return int(value) if value.is_integer() else value


def collect():
    a = {}
    print('Answer each question; press Enter to skip optional ones.\n')
    a['kind'] = ask('Regular rental or income-restricted (affordable)?', 'regular', choices=['regular', 'affordable'])
    a['space'] = ask('Whole apartment/home or a room in a shared apartment?', 'whole', choices=['whole', 'room'])
    a['community'] = ask('Community / building name', required=True)
    a['plan'] = ask('Floor plan or unit description (e.g. "2 bedroom, 2 bath" or "Room A in 4-bedroom apartment")',
                    required=True)
    a['unit_number'] = ask('Unit number, if the page names one')
    a['address'] = ask('Street address with city, state and ZIP (e.g. "300 Fieldstone Lane, Blacksburg, VA 24060")',
                       required=True)
    a['city'] = ask('City or town', required=True)
    print('Jurisdictions: ' + ', '.join(JURISDICTIONS))
    guess = 'Montgomery County' if a['city'].casefold() in {'blacksburg', 'christiansburg'} else None
    a['jurisdiction'] = ask('County or independent city', guess, required=True, choices=JURISDICTIONS)
    a['source_url'] = ask("Page these facts come from (property's own site or a county/HUD page)", required=True)
    if not a['source_url'].startswith('https://'):
        a['source_url'] = 'https://' + a['source_url'].removeprefix('http://')
    if listing_site(a['source_url']):
        print('  Note: that is a listing site, so the record will be saved unverified and flagged on /review.')
    a['website'] = ask("Property's own website", a['source_url'] if not listing_site(a['source_url']) else None)
    a['phone'] = ask("Leasing office phone (from the property's own page)")
    a['rent'] = ask('Monthly rent in dollars (blank if not published)', kind=number)
    if a['space'] == 'whole':
        a['bedrooms'] = ask('Bedrooms (0 for a studio)', kind=int)
    else:
        a['shared_bedrooms'] = ask('Bedrooms in the shared apartment', kind=int)
        a['shared_bathrooms'] = ask('Bathrooms in the shared apartment', kind=number)
        a['private_bathroom'] = yes('Private bathroom?') if yes('Does the page say whether the bathroom is private?') else None
    a['bathrooms'] = ask('Bathrooms for this unit/room', kind=number)
    a['square_feet'] = ask('Square feet', kind=int)
    print('Availability: ' + ', '.join(sorted(STATUSES - {'closed'})))
    a['status'] = ask('Availability status', 'contact_for_availability', choices=sorted(STATUSES - {'closed'}))
    a['available_from'] = ask('Available from (YYYY-MM-DD), if a date is given',
                              kind=lambda raw: date.fromisoformat(raw).isoformat())
    a['evidence'] = ask('What the page says about availability, in a sentence', required=True)
    if a['kind'] == 'affordable':
        a['program'] = ask('Program (e.g. "LIHTC 60% AMI", "HUD Section 8", "Fairfax County ADU")', required=True)
        a['program_evidence'] = ask('Where the page states the income restriction, in a sentence', required=True)
        a['program_source'] = ask('Page that documents the program', a['source_url'])
    a['minimum_age'] = ask('Minimum age if it is a 55+/62+ community', kind=int)
    a['student_friendly'] = yes('Student-friendly (near a campus, per-bedroom or academic-year leases)?',
                                a['city'].casefold() == 'blacksburg')
    a['utilities'] = ask('Utilities included, as the page says')
    a['lease_notes'] = ask('Lease term notes (e.g. "12-month lease", "Leasing for 2027-2028")')
    a['notes'] = ask('Other notes (amenities, conflicts you noticed)')
    return a


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help='show the record but never save it')
    args = parser.parse_args()
    rows = json.loads(RESOURCES_PATH.read_text())
    answers = collect()
    if yes('Look up a map pin with the US Census Geocoder?', True):
        try:
            from geocode import lookup
            point = lookup(answers['address'])
        except Exception as error:  # offline or the service is down; the listing still works without a pin
            print(f'  Lookup failed ({error}); saving without a map pin.')
        else:
            if point:
                answers['lat'], answers['lon'] = point
                print(f'  Pin: {point[0]}, {point[1]}')
            else:
                print('  No match; saving without a map pin.')
    record = build_record(answers, {r.get('id') for r in rows})
    print('\n' + json.dumps(record, indent=2, ensure_ascii=False))
    matches = similar(record, rows)
    if matches:
        print('\nAlready in the catalog for this community and size: ' + ', '.join(matches))
        print('If it is the same apartment, edit that record instead (or mark it verified on /review).')
        if not yes('Add this as a separate listing anyway?'):
            print('Not saved.')
            return 0
    errors = problems(record, rows)
    if errors:
        print('\nThis record would not show on the site:')
        print('\n'.join('  - ' + e for e in errors))
        return 1
    print('\nPasses the catalog checks.' + ('' if record['verified'] else
          ' Saved unverified: it stays hidden until someone confirms it from an official page.'))
    if args.dry_run or not yes('Save it to data/resources.json?', True):
        print('Not saved.')
        return 0
    rows.append(record)
    RESOURCES_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
    if not record['verified']:
        try:
            review = json.loads(REVIEW_PATH.read_text())
        except (OSError, ValueError):
            review = {'about': 'Team decisions from the /review page. hidden = kept out of every answer and list.'}
        decisions = review.get('decisions') or {}
        decisions[record['id']] = {'state': 'flagged', 'on': record['availability']['checked_on'],
                                   'note': 'Hand-added from a listing site → confirm on the property\'s own page or by phone, '
                                           'then set verified: true and last_verified to that date'}
        review['decisions'] = dict(sorted(decisions.items()))
        REVIEW_PATH.write_text(json.dumps(review, indent=2, ensure_ascii=False) + '\n')
    print(f"Saved {record['id']}. Next: python backend/catalog.py --check, then commit and push.")
    print(f"Its availability review is due {record['availability']['review_due']}; recheck it by then or it drops off.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
