"""Duplicate prevention and community browsing, without model or network calls."""
import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from catalog import (community_key, deduplicate_listings, filter_catalog, group_listings,
                     listing_key, load_catalog, validate_resources)

TODAY = date(2026, 10, 24)


def plans(card):
    """A grouped card's floor plans as the pages see them: each plan lists only what differs from its card."""
    return [{**card, **plan} for plan in card['floor_plans']]


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.row = next(r for r in load_catalog() if r['id'] == 'arbor-heights-one-bedroom')

    def test_duplicate_option_with_different_id_and_address_format_is_rejected(self):
        duplicate = copy.deepcopy(self.row)
        duplicate.update(id='new-import-id', name='Repeated import',
                         address='5203 8th Rd. S., Arlington, VA 22204',
                         floor_plan='  1 BEDROOM  ', monthly_rent=1400)
        self.assertEqual(listing_key(duplicate), listing_key(self.row))
        self.assertTrue(any('duplicate housing option' in e for e in validate_resources([self.row, duplicate])))
        self.assertEqual(len(deduplicate_listings([self.row, duplicate])), 1)

    def test_newer_closure_cannot_revive_an_older_available_snapshot(self):
        closed = copy.deepcopy(self.row)
        closed['id'] = 'new-import-id'
        closed['availability'].update(status='closed', checked_on='2026-10-25', review_due='2026-10-31')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'resources.json'
            path.write_text(json.dumps([self.row, closed]))
            self.assertEqual(load_catalog(path), [closed])
            self.assertEqual(filter_catalog(load_catalog(path), today=date(2026, 10, 25)), [])
        closed['availability']['checked_on'] = self.row['availability']['checked_on']
        self.assertEqual(deduplicate_listings([closed, self.row]), [closed])
        self.assertEqual(deduplicate_listings([self.row, closed]), [closed])

    def test_different_plans_and_ami_tiers_are_preserved_in_one_card(self):
        rows = [r for r in load_catalog() if r.get('community') == 'Glen Ridge Commons']
        self.assertEqual(len(deduplicate_listings(rows)), 3)
        cards = group_listings(rows)
        self.assertEqual(len(cards), 1)
        self.assertEqual(len(cards[0]['floor_plans']), 3)
        self.assertEqual(len({p['floor_plan'] for p in cards[0]['floor_plans']}), 3)
        self.assertEqual(cards[0]['monthly_rent'], min(p['monthly_rent'] for p in rows))

    def test_same_name_different_buildings_and_same_street_are_not_merged(self):
        other = dict(self.row, id='another-address', address='5303 8th Road South, Arlington, VA 22204')
        self.assertEqual(len(group_listings([self.row, other])), 2)
        no_number = dict(self.row, address='8th Road South, Arlington, VA', community='Community A')
        other = dict(no_number, id='b', community='Community B')
        self.assertEqual(len(group_listings([no_number, other])), 2)
        agencies = [dict(self.row, id='program-a', type='housing_authority'),
                    dict(self.row, id='program-b', type='housing_authority')]
        self.assertEqual(len(group_listings(agencies)), 2)

    def test_groups_keep_only_matching_options_and_unknown_rents_sort_last(self):
        rows = filter_catalog(load_catalog(), {'types': ['affordable_listing', 'rental_listing'],
                                              'max_budget_per_month': 1500}, today=TODAY)
        cards = group_listings(rows, sort='rent_asc')
        self.assertTrue(cards)
        self.assertEqual(len({community_key(c) for c in cards}), len(cards))
        self.assertTrue(all(p['monthly_rent'] <= 1500 for c in cards for p in plans(c)))
        prices = [c['monthly_rent'] for c in cards]
        self.assertEqual(prices, sorted(prices))
        unknown = dict(self.row, id='unknown', address='10 Unknown Rd, Arlington, VA', monthly_rent=None)
        cards = group_listings([unknown, self.row], sort='rent_asc')
        self.assertIsNone(cards[-1]['monthly_rent'])


class GroupedApiTests(unittest.TestCase):
    def setUp(self):
        from app import app
        self.client = app.test_client()
        # The catalog's fixed source-review date keeps these tests deterministic.
        class FixedDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 10, 24)
        clock = patch('catalog.date', FixedDate)
        clock.start()
        self.addCleanup(clock.stop)

    def test_flat_response_remains_compatible_and_grouped_count_is_communities(self):
        flat = self.client.get('/api/listings').get_json()
        grouped = self.client.get('/api/listings?group_by=community').get_json()
        self.assertLess(grouped['count'], flat['count'])
        self.assertEqual(grouped['option_count'], flat['count'])
        self.assertEqual(sum(len(c['floor_plans']) for c in grouped['listings']), flat['count'])
        self.assertTrue(all('floor_plans' not in r for r in flat['listings']))

    def test_grouped_plans_merge_back_to_full_records(self):
        flat = {r['id']: r for r in self.client.get('/api/listings').get_json()['listings']}
        for card in self.client.get('/api/listings?group_by=community').get_json()['listings']:
            for plan in plans(card):
                expected = {k: v for k, v in flat[plan['id']].items()}
                self.assertEqual({k: v for k, v in plan.items() if k != 'floor_plans' and v is not None},
                                 {k: v for k, v in expected.items() if v is not None})

    def test_map_pins_are_small(self):
        pins = self.client.get('/api/listings?fields=pins').get_json()['listings']
        self.assertTrue(pins and all(isinstance(p['lat'], float) and set(p) <= {'id', 'community', 'name', 'floor_plan', 'lat', 'lon', 'monthly_rent', 'rent_basis', 'rental_space', 'source_url', 'availability'} for p in pins))

    def test_budget_and_availability_apply_before_grouping(self):
        response = self.client.get('/api/listings?group_by=community&max_rent=1500&status=available_now&sort=rent_asc')
        self.assertEqual(response.status_code, 200)
        cards = response.get_json()['listings']
        self.assertTrue(cards)
        self.assertTrue(all(p['monthly_rent'] <= 1500 and p['availability']['status'] == 'available_now'
                            for c in cards for p in plans(c)))
        self.assertEqual([c['monthly_rent'] for c in cards], sorted(c['monthly_rent'] for c in cards))

    def test_new_budget_options_have_sources_and_unknown_prices_do_not_match(self):
        cards = self.client.get('/api/listings?group_by=community&max_rent=1500').get_json()['listings']
        ids = {p['id'] for c in cards for p in plans(c)}
        self.assertTrue({'virginia-gardens-one-bedroom', 'gates-ballston-studio', 'harvey-hall-studio'} <= ids)
        self.assertNotIn('fields-manassas-community', ids)
        self.assertNotIn('terwilliger-place-community', ids)
        affordable = self.client.get('/api/listings?housing_type=affordable&max_rent=1500').get_json()['listings']
        self.assertIn('virginia-gardens-one-bedroom', {r['id'] for r in affordable})
        self.assertNotIn('gates-ballston-studio', {r['id'] for r in affordable})

    def test_invalid_group_and_sort_are_reported(self):
        for query in ['group_by=unknown', 'sort=unknown']:
            self.assertEqual(self.client.get('/api/listings?' + query).status_code, 400)


if __name__ == '__main__':
    unittest.main()
