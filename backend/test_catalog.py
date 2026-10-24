"""Offline catalog and matching checks; no model or external website calls."""
import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import catalog
from catalog import effective_availability, filter_catalog, load_catalog, validate_resources
import matcher

REVIEW_DAY = date(2026, 10, 24)

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.rows = load_catalog()
        self.row = copy.deepcopy(self.rows[0])

    def test_production_catalog_is_valid_and_covers_core_nova_jurisdictions(self):
        raw = json.loads(catalog.RESOURCES_PATH.read_text())
        self.assertEqual(validate_resources(raw), [])
        self.assertEqual(len({r['id'] for r in raw}), len(raw))
        core = {'Arlington County','Fairfax County','Loudoun County','Prince William County','Alexandria City','Fairfax City','Falls Church City','Manassas City','Manassas Park City'}
        self.assertEqual({r['jurisdiction'] for r in raw}, core | {'Northern Virginia'})
        self.assertTrue(all(r['sources'] for r in raw))
        self.assertTrue(all(r['availability']['evidence'] for r in raw if r['type'] == 'affordable_listing'))

    def test_unverified_and_invalid_records_are_not_loaded(self):
        invalid = copy.deepcopy(self.row)
        invalid['source_url'] = 'javascript:alert(1)'
        draft = copy.deepcopy(self.row)
        draft['verified'] = False
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'resources.json'
            path.write_text(json.dumps([self.row, invalid, draft]))
            self.assertEqual(load_catalog(path), [self.row])

    def test_closed_or_overdue_records_are_excluded(self):
        rows = []
        for status in ('available_now','closed','waitlist_open'):
            row = copy.deepcopy(self.row)
            row['availability']['status'] = status
            rows.append(row)
        self.assertEqual(len(filter_catalog(rows, today=REVIEW_DAY)), 2)
        self.assertEqual(filter_catalog(rows, today=date(2026,11,1)), [])
        self.assertEqual(effective_availability(rows[0], date(2026,11,1))['status'], 'needs_recheck')
        self.assertEqual(rows[0]['availability']['status'], 'available_now')
        self.assertEqual(filter_catalog(rows, today=date(2026,10,23)), [])

    def test_budget_does_not_treat_unknown_or_promotion_only_rent_as_a_match(self):
        rows = filter_catalog(self.rows, {'types':['affordable_listing'], 'max_budget_per_month':1600}, today=REVIEW_DAY)
        self.assertTrue(rows)
        self.assertTrue(all(isinstance(r['monthly_rent'], (int,float)) and r['monthly_rent'] <= 1600 for r in rows))
        self.assertNotIn('spire-one-bedroom', {r['id'] for r in rows})
        self.assertNotIn('linden-senior', {r['id'] for r in rows})
        self.assertEqual(filter_catalog(self.rows, {'types':['affordable_listing'],'max_budget_per_month':0}, today=REVIEW_DAY), [])

    def test_accessibility_requires_an_explicit_true(self):
        rows = [dict(self.row, accessible=value) for value in (None, False, True)]
        self.assertEqual(len(filter_catalog(rows, {'needs_accessible':True}, today=REVIEW_DAY)),1)

    def test_waitlists_are_included_for_planning_but_not_tonight(self):
        waitlist = next(r for r in self.rows if r['id']=='riverwoods-one-bedroom')
        self.assertTrue(filter_catalog([waitlist], {'urgency':'planning'}, today=REVIEW_DAY))
        self.assertEqual(filter_catalog([waitlist], {'urgency':'emergency'}, today=REVIEW_DAY), [])

    def test_senior_age_and_studio_filter(self):
        senior = next(r for r in self.rows if r['id']=='park-place-senior-one-bedroom')
        self.assertEqual(filter_catalog([senior], {'age':22}, today=REVIEW_DAY), [])
        self.assertTrue(filter_catalog([senior], {'age':60}, today=REVIEW_DAY))
        studios = filter_catalog(self.rows, {'types':['affordable_listing'],'bedrooms':0}, today=REVIEW_DAY)
        self.assertTrue(studios)
        self.assertTrue(all(r['bedrooms']==0 for r in studios))

    def test_city_and_county_are_distinguished(self):
        listings = [r for r in self.rows if r['type'] == 'affordable_listing']
        city = filter_catalog(listings, {'locations':['Fairfax City']}, today=REVIEW_DAY)
        county = filter_catalog(listings, {'locations':['Fairfax County']}, today=REVIEW_DAY)
        self.assertTrue(city and county)
        self.assertTrue(all(r['jurisdiction']=='Fairfax City' for r in city))
        self.assertTrue(all(r['jurisdiction']=='Fairfax County' for r in county))
        park = filter_catalog(listings, {'locations':['Manassas Park']}, today=REVIEW_DAY)
        self.assertTrue(all(r['city']=='Manassas Park' for r in park))

    def test_malformed_model_filters_fall_back_to_explicit_form_values(self):
        with patch.object(matcher,'ask_gemma',return_value='{"types":null,"locations":false,"max_budget_per_month":"free","needs_accessible":"yes","urgency":null}'):
            filters = matcher.extract_filters('Location: Fairfax County.\nMaximum monthly budget: $1500.\nI need a room.')
        self.assertEqual(filters['locations'], ['Fairfax County'])
        self.assertEqual(filters['max_budget_per_month'], 1500)
        self.assertEqual(filters['types'], [])
        self.assertFalse(filters['needs_accessible'])
        self.assertEqual(filters['urgency'],'soon')

    def test_invalid_model_json_keeps_structured_budget(self):
        with patch.object(matcher,'ask_gemma',return_value='not json'):
            filters = matcher.extract_filters('Location: Northern Virginia.\nMaximum monthly budget: $900.\nI need housing.')
        self.assertEqual(filters['max_budget_per_month'],900)

    def test_validator_rejects_duplicate_ids_and_missing_evidence(self):
        self.assertTrue(validate_resources([self.row,self.row]))
        self.row['availability']['evidence'] = None
        self.assertTrue(validate_resources([self.row]))

    def test_empty_match_does_not_generate_an_answer(self):
        with patch.object(matcher,'extract_filters',return_value={'types':['affordable_listing'],'max_budget_per_month':1}), patch.object(matcher,'ask_gemma') as model:
            _, answer = matcher.find_help('I can pay $1 monthly.')
        self.assertIn('211',answer)
        model.assert_not_called()

class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026,10,24)

class ListingsApiTests(unittest.TestCase):
    def setUp(self):
        from app import app
        self.client=app.test_client()
        self.clock=patch.object(catalog,'date',FixedDate)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_read_catalog_without_ai(self):
        with patch.object(matcher,'ask_gemma',side_effect=AssertionError('No AI should be called')):
            response=self.client.get('/api/listings')
        self.assertEqual(response.status_code,200)
        body=response.get_json()
        self.assertEqual(body['count'],len(body['listings']))
        self.assertTrue(body['count'])
        self.assertTrue(all(r['availability']['status']!='closed' for r in body['listings']))

    def test_filters_and_validation(self):
        response=self.client.get('/api/listings?location=Arlington&max_rent=1500&bedrooms=1')
        self.assertEqual(response.status_code,200)
        rows=response.get_json()['listings']
        self.assertTrue(rows)
        self.assertTrue(all(r['city']=='Arlington' and r['monthly_rent']<=1500 and r['bedrooms']==1 for r in rows))
        for query in ('max_rent=NaN','max_rent=-1','bedrooms=1.5','accessible=yes','status=closed','age=abc'):
            self.assertEqual(self.client.get('/api/listings?'+query).status_code,400,query)
        rows=self.client.get('/api/listings?status=waitlist_open').get_json()['listings']
        self.assertTrue(rows)
        self.assertTrue(all(r['availability']['status']=='waitlist_open' for r in rows))

if __name__=='__main__':
    unittest.main()
