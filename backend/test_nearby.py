"""'Near my office' questions: the place is read from the question, found, and homes ranked by distance.

Google calls are mocked, so this runs offline. Run: python backend/test_nearby.py
"""
import unittest
from unittest.mock import patch

import nearby

TYSONS = (38.9187, -77.2311)


def fake_post(url, body, mask):
    if url == nearby.PLACES_TEXT_URL:
        return {"places": [{"displayName": {"text": "Inova Fairfax Hospital"}, "formattedAddress": "3300 Gallows Rd",
                            "location": {"latitude": 38.8574, "longitude": -77.2285}}]}
    return [{"originIndex": i, "duration": "600s", "condition": "ROUTE_EXISTS"} for i in range(len(body["origins"]))]


class NearbyTests(unittest.TestCase):
    def setUp(self):
        nearby._cache.clear()

    def test_reads_the_place_out_of_the_question(self):
        self.assertEqual(nearby.extract_place("I need a place near my office at 1800 Tysons Blvd")[0], "1800 Tysons Blvd")
        self.assertEqual(nearby.extract_place("something close to Inova Fairfax Hospital?")[0], "Inova Fairfax Hospital")
        self.assertEqual(nearby.extract_place("near my job"), (None, "job"))
        self.assertEqual(nearby.extract_place("I need a 2 bedroom apartment"), (None, None))

    def test_ordinary_sentences_are_not_places(self):
        for q in ["I was kicked out by my landlord and have nowhere to sleep tonight", "around $1200", "near term",
                  "something by next month", "close to being evicted", "pay by check", "around Christmas I'll be homeless",
                  "by the way, do you have studios", "near the end of the month", "close to 3 people"]:
            with self.subTest(q):
                self.assertEqual(nearby.extract_place(q), (None, None))

    @patch.object(nearby, "_key", return_value="")
    def test_near_me_uses_the_shared_location(self, _):
        text = nearby.answer("Homes near my current location", {"coords": {"lat": 38.8816, "lon": -77.0910}})
        self.assertIn("Closest reviewed homes", text)
        self.assertIn("your location", text)
        self.assertIn("outside the areas", nearby.answer("near me", {"coords": {"lat": 40.71, "lon": -74.0}}))
        self.assertIn("Near me", nearby.answer("anything near me?", {}))  # no location shared: explain how

    def test_unpublished_rent_gets_a_labeled_estimate_not_a_fake_price(self):
        from advisor import rent_estimate
        from catalog import filter_catalog, load_catalog
        rows = filter_catalog(load_catalog())
        home = next(r for r in rows if r["type"] == "affordable_listing" and r.get("monthly_rent") is None and r.get("lat"))
        est = rent_estimate(home, rows)
        self.assertTrue(est and est["low"] <= est["high"] and "similar reviewed homes" in est["basis"])
        self.assertIsNone(home.get("monthly_rent"))  # the record itself is never changed
        priced = next(r for r in rows if isinstance(r.get("monthly_rent"), (int, float)))
        self.assertIsNone(rent_estimate(priced, rows))  # a published rent is never replaced by an estimate

    def test_asks_for_the_address_when_only_my_office_is_given(self):
        self.assertIn("address", nearby.answer("Find me something near my office"))

    @patch.object(nearby, "_key", return_value="test")
    @patch.object(nearby, "_post", side_effect=fake_post)
    @patch.object(nearby, "census_lookup", return_value=TYSONS)
    def test_street_address_lists_closest_homes_with_commutes(self, *_):
        text = nearby.answer("near my office at 1800 Tysons Blvd")
        self.assertIn("Closest reviewed homes to 1800 Tysons Blvd", text)
        self.assertIn("10 min by car", text)
        self.assertEqual(text.count("\n- "), nearby.MAX_HOMES)

    @patch.object(nearby, "_key", return_value="test")
    @patch.object(nearby, "_post", side_effect=fake_post)
    def test_named_place_is_found_with_google_places(self, *_):
        self.assertIn("Inova Fairfax Hospital", nearby.answer("close to Inova Fairfax Hospital"))

    def test_places_outside_the_area_are_refused(self):
        self.assertIn("outside the areas", nearby.answer("near the harbor in Baltimore"))

    @patch.object(nearby, "_key", return_value="")
    def test_works_without_google_using_straight_line_distance(self, _):
        text = nearby.answer("near George Mason University")
        self.assertIn("Distances are straight-line", text)


if __name__ == "__main__":
    unittest.main()
