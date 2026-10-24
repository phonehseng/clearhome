"""Emergency shelters and intake lines: never hidden for lacking a confirmed bed, never shown as a guaranteed one.

Run: python backend/test_emergency_services.py
"""
import copy
import unittest
from datetime import date

from catalog import filter_catalog, load_catalog

TODAY = date(2026, 10, 24)


class EmergencyServiceTests(unittest.TestCase):
    def setUp(self):
        self.shelter = copy.deepcopy(next(r for r in load_catalog() if r["type"] == "emergency_shelter"))
        self.shelter["availability"] = {"status": "contact_for_availability", "checked_on": "2026-10-24", "review_due": "2026-10-31"}
        self.home = copy.deepcopy(next(r for r in load_catalog() if r["type"] == "affordable_listing" and r.get("availability")))
        self.home["availability"] = dict(self.home["availability"], status="contact_for_availability", checked_on="2026-10-24", review_due="2026-10-31")

    def test_call_to_confirm_shelter_stays_in_emergency_results(self):
        rows = filter_catalog([self.shelter, self.home], {"urgency": "emergency"}, today=TODAY)
        self.assertEqual([r["id"] for r in rows], [self.shelter["id"]])  # the waitlist-style home is not a bed tonight

    def test_lapsed_review_reverts_to_call_to_confirm_instead_of_hiding(self):
        rows = filter_catalog([self.shelter], {}, today=date(2026, 11, 15))
        self.assertEqual(rows[0]["availability"]["status"], "contact_for_availability")
        self.assertEqual(filter_catalog([self.home], {}, today=date(2026, 11, 15)), [])  # housing listings still expire

    def test_budget_filter_never_drops_free_or_unknown_cost_emergency_help(self):
        rows = filter_catalog([self.shelter], {"max_budget_per_month": 100}, today=TODAY)
        self.assertEqual(len(rows), 1)


    def test_blacksburg_tonight_lists_real_overnight_help_and_closed_shelters_last(self):
        from advisor import options
        shelters = options({"location": "Blacksburg", "tonight": True})["shelters"]
        names = [r["name"] for r in shelters]
        self.assertTrue(any("after-hours" in n for n in names))
        self.assertEqual(shelters[-1].get("intake_status"), "closed")  # To Our House opens Nov 7
        self.assertTrue(all(r.get("region") == "New River Valley" for r in shelters))
        for r in shelters:  # confidential places never get an address to walk to
            if r.get("confidential_location"):
                self.assertFalse(r.get("public_intake_address"))


if __name__ == "__main__":
    unittest.main()
