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
