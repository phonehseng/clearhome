"""Expansion data must not turn a directory entry into a vacant budget match."""
import json
import unittest
from datetime import date

from catalog import RESOURCES_PATH, community_key, filter_catalog, group_listings, validate_resources


class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(RESOURCES_PATH.read_text())
        cls.batch = [r for r in cls.rows if r.get('catalog_batch') == 'nova-expansion-2026-10-24']
        cls.today = date(2026, 10, 24)

    def test_reviewed_batch_is_valid_and_does_not_repeat_existing_communities(self):
        self.assertTrue(self.batch)
        self.assertEqual(validate_resources(self.rows), [])
        earlier = {community_key(r) for r in self.rows if not r.get('catalog_batch')}
        self.assertFalse(earlier.intersection(community_key(r) for r in self.batch))
        for card in group_listings(self.batch):
            self.assertEqual(len({r['floor_plan'] for r in card['floor_plans']}), len(card['floor_plans']))

    def test_directory_records_do_not_claim_vacancies_open_waitlists_or_unit_prices(self):
        for row in self.batch:
            if row['record_kind'] != 'community':
                continue
            with self.subTest(row=row['id']):
                self.assertIsNone(row['monthly_rent'])
                self.assertIsNone(row['accessible'])
                self.assertIsNone(row['bedrooms'])
                self.assertIsNone(row['availability']['available_from'])
                self.assertIn(row['availability']['status'], {'contact_for_availability', 'leasing'})
                self.assertTrue(row['affordability']['source_url'].startswith('https://'))

    def test_only_quoted_rents_can_match_a_budget_and_programs_cannot_solve_tonight(self):
        matches = filter_catalog(self.batch, {'max_budget_per_month': 1500}, self.today)
        self.assertTrue(any(r['id'] == 'nova-broadfalls-efficiency' for r in matches))
        self.assertTrue(all(isinstance(r['monthly_rent'], (int, float)) and r['monthly_rent'] <= 1500 for r in matches))
        directories = [r for r in self.batch if r['record_kind'] == 'community']
        self.assertEqual(filter_catalog(directories, {'urgency': 'emergency'}, self.today), [])
        self.assertEqual(filter_catalog(self.batch, today=date(2026, 11, 1)), [])


if __name__ == '__main__':
    unittest.main()
