"""The add-listing helper builds records the site will actually show, and holds back listing-site data.

Run: python backend/test_add_listing.py
"""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

import add_listing
import catalog

TODAY = date(2026, 10, 25)
WHOLE = {'kind': 'regular', 'space': 'whole', 'community': 'Maple Court', 'plan': '2 bedroom, 1 bath',
         'address': '100 Maple Court, Blacksburg, VA 24060', 'city': 'Blacksburg', 'jurisdiction': 'Montgomery County',
         'source_url': 'https://maplecourtapts.example.com/floorplans', 'website': 'https://maplecourtapts.example.com/',
         'phone': '(540) 555-0100', 'rent': 1250, 'bedrooms': 2, 'bathrooms': 1, 'status': 'available_now',
         'evidence': 'The provider lists a 2-bedroom available now at $1,250.', 'lat': 37.23, 'lon': -80.41}


class AddListingTests(unittest.TestCase):
    def test_official_whole_apartment_is_shown(self):
        record = add_listing.build_record(WHOLE, today=TODAY)
        self.assertEqual(add_listing.problems(record, []), [])
        self.assertTrue(record['verified'])
        self.assertEqual((record['region'], record['area']), ('New River Valley', 'Blacksburg'))
        self.assertEqual(record['phone'], '540-555-0100')
        self.assertEqual(record['availability']['review_due'], '2026-11-01')
        shown = catalog.filter_catalog([record], {'location': 'Blacksburg'}, today=TODAY)
        self.assertEqual([r['id'] for r in shown], [record['id']])

    def test_room_and_affordable_records_pass_the_room_rules(self):
        room = dict(WHOLE, space='room', plan='Room A in 4-bedroom apartment', rent=650, shared_bedrooms=4,
                    shared_bathrooms=2, bedrooms=None)
        record = add_listing.build_record(room, today=TODAY)
        self.assertEqual((record['bedrooms'], record['price_unit'], record['rent_basis']), (1, 'per_person', 'per_person_monthly'))
        self.assertEqual(add_listing.problems(record, []), [])
        nova = dict(WHOLE, kind='affordable', city='Arlington', jurisdiction='Arlington County', address='1 Test St, Arlington, VA 22201',
                    program='LIHTC 60% AMI', program_evidence='County list names it as a 60% AMI committed affordable unit.')
        record = add_listing.build_record(nova, today=TODAY)
        self.assertEqual((record['type'], record['area']), ('affordable_listing', 'Arlington County'))
        self.assertEqual(add_listing.problems(record, []), [])

    def test_listing_site_data_is_saved_unverified(self):
        record = add_listing.build_record(dict(WHOLE, source_url='https://www.apartments.com/maple-court/abc/'), today=TODAY)
        self.assertFalse(record['verified'])
        self.assertIsNone(record['last_verified'])
        self.assertEqual(record['sources'][0]['role'], 'listing_site')
        self.assertEqual(catalog.filter_catalog([record], today=TODAY), [])

    def test_duplicates_are_caught_and_ids_stay_unique(self):
        first = add_listing.build_record(WHOLE, today=TODAY)
        second = add_listing.build_record(WHOLE, {first['id']}, today=TODAY)
        self.assertNotEqual(first['id'], second['id'])
        self.assertTrue(any('duplicate housing option' in e for e in add_listing.problems(second, [first])))
        # An unverified record for the same community and size is pointed out too, so it gets edited, not copied.
        held = dict(first, verified=False, floor_plan='1BR unit', address='100 Maple Ct, Blacksburg, VA 24060')
        self.assertEqual(add_listing.similar(second, [held]), [first['id']])

    def test_prompts_save_a_complete_record(self):
        folder = Path(tempfile.mkdtemp())
        resources, review = folder / 'resources.json', folder / 'listing_review.json'
        resources.write_text('[]')
        answers = iter(['', '', 'Maple Court', '2 bedroom, 1 bath', '', '100 Maple Court, Blacksburg, VA 24060',
                        'Blacksburg', '', 'https://www.zillow.com/maple', '', '5405550100', '$1,250', '2', '1', '',
                        'available_now', 'not-a-date', '2026-11-15', 'Listed as available Nov 15.', '', '', '', '', '',
                        'n', 'y'])
        with patch.object(add_listing, 'RESOURCES_PATH', resources), patch.object(add_listing, 'REVIEW_PATH', review), \
                patch('builtins.input', lambda _: next(answers)), patch('sys.argv', ['add_listing.py']), redirect_stdout(io.StringIO()):
            self.assertEqual(add_listing.main(), 0)
        saved = json.loads(resources.read_text())[0]
        self.assertEqual((saved['monthly_rent'], saved['jurisdiction'], saved['availability']['available_from']),
                         (1250, 'Montgomery County', '2026-11-15'))
        self.assertFalse(saved['verified'])
        self.assertEqual(json.loads(review.read_text())['decisions'][saved['id']]['state'], 'flagged')


if __name__ == '__main__':
    unittest.main()
