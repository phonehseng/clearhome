import json
import unittest
from unittest.mock import patch
from discover import extract_candidates, approved_sources
from catalog import filter_catalog,load_catalog,validate_resources
from datetime import date

class DiscoveryTests(unittest.TestCase):
    def test_invented_names_and_unsupported_claims_rejected(self):
        reply={'listings':[{'name':'Made Up','category':'affordable','evidence':{'name':'Made Up is available'}},{'name':'Actual House','category':'affordable','evidence':{'name':'Actual House rents apartments.','rent':'$500','program':'Income restricted'}}]}
        with patch('discover.ask_gemma',return_value=json.dumps(reply)):
            rows=extract_candidates({'name':'Actual House','discovery_url':'https://example.org'},'Actual House rents apartments.')
        self.assertEqual(len(rows),1)
        self.assertFalse(rows[0]['verified'])
        self.assertIsNone(rows[0]['monthly_rent'])
        self.assertEqual(rows[0]['suggested_category'],'unknown')
        self.assertIsNone(rows[0]['extraction_evidence']['rent'])
        self.assertEqual(filter_catalog(rows),[])

    def test_source_allowlist(self):
        with self.assertRaises(ValueError):approved_sources(['https://localhost/private'])

    def test_both_categories_filter_by_budget(self):
        rows=load_catalog();today=date(2026,10,24)
        selected=filter_catalog(rows,{'types':['affordable_listing','rental_listing'],'max_budget_per_month':2000},today)
        self.assertTrue(any(r['type']=='rental_listing' for r in selected))
        self.assertTrue(any(r['type']=='affordable_listing' for r in selected))
        self.assertTrue(all(r['monthly_rent']<=2000 for r in selected))
        regular=next(r for r in rows if r['type']=='rental_listing')
        regular['affordability']=None
        self.assertTrue(validate_resources([regular]))
        self.assertEqual(filter_catalog([regular],today=today),[])

    def test_affordable_label_alone_cannot_publish(self):
        row=next(r for r in load_catalog() if r['type']=='affordable_listing')
        row['affordability']=None
        self.assertTrue(validate_resources([row]))
        self.assertEqual(filter_catalog([row],today=date(2026,10,24)),[])

if __name__=='__main__':unittest.main()
