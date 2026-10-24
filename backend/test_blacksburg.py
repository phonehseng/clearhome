"""Regional isolation, room pricing, and advertised eligibility; no external calls."""
import copy
import unittest
from datetime import date
from unittest.mock import patch

from catalog import filter_catalog, load_catalog, senior_only, validate_resources
from advisor import area_for, options, _pick
from prompt_tools import keyword_filters


class BlacksburgTests(unittest.TestCase):
    def setUp(self):
        self.rows = load_catalog()
        self.batch = [r for r in self.rows if r.get('catalog_batch') == 'blacksburg-students-2026-10-24']
        self.today = date(2026, 10, 24)

    def test_catalog_and_offered_room_semantics(self):
        self.assertTrue(self.batch)
        self.assertEqual(validate_resources(self.rows), [])
        for row in self.batch:
            if row.get('rental_space') != 'room':
                continue
            self.assertEqual(row['bedrooms'], 1)
            self.assertEqual(row['price_unit'], 'per_person')
            self.assertIsNone(row['square_feet'])
            self.assertIsNone(row['accessible'])
            self.assertTrue(row['lease_responsibility'])
        invalid = copy.deepcopy(next(r for r in self.batch if r.get('rental_space') == 'room'))
        invalid['price_unit'] = 'per_home'
        self.assertTrue(validate_resources([invalid]))

    def test_regions_do_not_leak_into_each_other_including_regional_services(self):
        for location in ['Northern Virginia', 'nova', 'Northern VA']:
            matches = filter_catalog(self.rows, {'locations': [location]}, self.today)
            self.assertTrue(matches)
            self.assertFalse(any(r.get('region') == 'New River Valley' for r in matches))
        matches = filter_catalog(self.rows, {'locations': ['Blacksburg']}, self.today)
        self.assertTrue(matches)
        self.assertTrue(all(r.get('region') == 'New River Valley' for r in matches))
        self.assertIn('blacksburg-wrc-emergency', {r['id'] for r in matches})
        self.assertFalse(any(r.get('jurisdiction') == 'Northern Virginia' for r in matches))

    def test_student_budget_keeps_real_room_prices_and_excludes_full_apartment_costs(self):
        matches = filter_catalog(self.rows, {'types': ['rental_listing', 'affordable_listing'], 'locations': ['Blacksburg'], 'rental_space': 'room',
                                            'max_budget_per_month': 1000, 'age_group': 'general'}, self.today)
        self.assertGreater(len(matches), 5)
        self.assertTrue(all(r['monthly_rent'] <= 1000 and r['price_unit'] == 'per_person' for r in matches))
        self.assertFalse(any(r.get('community') == 'The Mill at Blacksburg' for r in matches))
        whole = filter_catalog(self.rows, {'locations': ['Blacksburg'], 'rental_space': 'entire_home'}, self.today)
        mill = [r for r in whole if r.get('community') == 'The Mill at Blacksburg']
        self.assertEqual({r['monthly_rent'] for r in mill}, {1100, 1300, 1680})
        self.assertTrue(all(r['lease_type'] == 'joint' for r in mill))

    def test_conflicting_dates_are_not_presented_as_confirmed_move_in(self):
        conflicts = [r for r in self.batch if 'Date conflict:' in r.get('notes', '')]
        self.assertTrue(conflicts)
        for row in conflicts:
            self.assertEqual(row['availability']['status'], 'contact_for_availability')
            self.assertIsNone(row['availability']['available_from'])
            self.assertIsNone(row['lease_start'])
        future = [r for r in self.batch if r.get('lease_start')]
        self.assertTrue(future)
        self.assertTrue(all(r['availability']['status'] == 'upcoming' and r['lease_start'] > self.today.isoformat() for r in future))

    def test_eligibility_filter_does_not_turn_disability_exceptions_into_age_rules(self):
        homes = [r for r in self.rows if r['type'] in {'affordable_listing', 'rental_listing'}]
        general = filter_catalog(homes, {'age_group': 'general'}, self.today)
        seniors = filter_catalog(homes, {'age_group': 'senior'}, self.today)
        self.assertTrue(general and seniors)
        self.assertTrue(all(not senior_only(r) for r in general))
        self.assertTrue(all(senior_only(r) for r in seniors))
        self.assertIn('nova-arlington-county-the-carlin', {r['id'] for r in general})

    def test_aliases_find_form_and_advisor_choose_the_requested_region(self):
        for name in ['Blacksburg, VA', 'Virginia Tech']:
            self.assertEqual(area_for(name), 'Blacksburg')
        filters, confident = keyword_filters('student room under $1000 near Virginia Tech')
        self.assertTrue(confident)
        self.assertEqual(filters['locations'], ['Blacksburg'])
        self.assertEqual(filters['rental_space'], 'room')
        picked = _pick(self.rows, 'rent assistance in Blacksburg')
        self.assertTrue(picked)
        self.assertTrue(all(r.get('region') == 'New River Valley' for r in picked))
        result = options({'location': 'Blacksburg', 'budget': 1000, 'rental_space': 'room', 'tonight': True})
        self.assertEqual(result['listings'], [])
        self.assertTrue(result['shelters'])
        self.assertTrue(all(r['region'] == 'New River Valley' for r in result['programs'] + result['shelters']))


class BlacksburgApiTests(unittest.TestCase):
    def setUp(self):
        from app import app
        self.client = app.test_client()

    def test_room_and_eligibility_filters_validate_and_apply_before_grouping(self):
        response = self.client.get('/api/listings?location=Blacksburg&rental_space=room&max_rent=1000&age_group=general&group_by=community')
        self.assertEqual(response.status_code, 200)
        cards = response.get_json()['listings']
        self.assertGreater(len(cards), 3)
        self.assertTrue(all(p['rental_space'] == 'room' and p['monthly_rent'] <= 1000 for c in cards for p in c['floor_plans']))
        for query in ['age_group=bogus', 'rental_space=bogus']:
            self.assertEqual(self.client.get('/api/listings?' + query).status_code, 400)
        with self.client.get('/rental-labels.js') as response:
            self.assertEqual(response.status_code, 200)

    def test_lease_guide_preserves_per_person_price_dates_and_responsibility(self):
        row = next(r for r in load_catalog() if r.get('rent_basis') == 'per_person_installment')
        with patch('lease_journey.retrieve_public_document') as retrieve:
            data = self.client.get('/api/listings/' + row['id'] + '/lease').get_json()
        retrieve.assert_not_called()
        for key in ['rental_space', 'price_unit', 'lease_type', 'lease_start', 'lease_end', 'rent_basis', 'lease_responsibility']:
            self.assertEqual(data['listing'][key], row[key])


if __name__ == '__main__':
    unittest.main()
