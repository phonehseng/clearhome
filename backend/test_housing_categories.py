import unittest
from datetime import date
from catalog import filter_catalog, load_catalog, validate_resources


class HousingCategoryTests(unittest.TestCase):
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

if __name__ == '__main__':
    unittest.main()
