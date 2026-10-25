"""Walking-distance search tests with mocked Google responses (no network, no real keys).

Run: python backend/test_walkable.py
"""
import os
import unittest
from unittest.mock import patch

import walkable

HOME = {"id": "home-1", "name": "Test Homes", "community": "Test Homes", "type": "affordable_listing", "address": "1 Main St, Arlington, VA",
        "jurisdiction": "Arlington County", "lat": 38.85, "lon": -77.1, "monthly_rent": 1200, "who_it_serves": "Income-restricted",
        "availability": {"status": "available_now"}, "source_url": "https://provider.example/home", "verified": True}
NO_COORDS = {**HOME, "id": "home-2", "name": "No Pin Homes", "community": "No Pin Homes", "lat": None, "lon": None}
PLACE = {"id": "place-1", "displayName": {"text": "Corner Market"}, "location": {"latitude": 38.851, "longitude": -77.101},
         "formattedAddress": "2 Main St", "businessStatus": "OPERATIONAL", "primaryType": "supermarket"}


def fake_post(places=(PLACE,), matrix=None):
    def post(url, body, mask, timeout=12):
        if url == walkable.PLACES_URL:
            return {"places": list(places)}
        if url == walkable.MATRIX_URL:
            return matrix if matrix is not None else [{"originIndex": 0, "destinationIndex": 0, "duration": "420s", "distanceMeters": 500, "condition": "ROUTE_EXISTS"}]
        raise AssertionError("unexpected URL")
    return post


class WalkableTests(unittest.TestCase):
    def setUp(self):
        walkable._cache.clear()
        patcher = patch.dict(os.environ, {"GOOGLE_MAPS_SERVER_API_KEY": "test-key"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_search(self, prompt, rows=(HOME,), **post_kwargs):
        with patch.object(walkable, "load_catalog", return_value=list(rows)), \
             patch.object(walkable, "filter_catalog", side_effect=lambda rows, f: list(rows)), \
             patch.object(walkable, "_post", side_effect=fake_post(**post_kwargs)):
            return walkable.search(prompt)

    def test_keyword_parsing_needs_no_ai(self):
        f = walkable.parse_request("Affordable housing under $1,500 with a supermarket within a 10-minute walk in Arlington")
        self.assertEqual((f["max_rent"], f["amenity"], f["max_walk_minutes"], f["area"], f["strict"]), (1500.0, "supermarket", 10, "Arlington County", True))
        self.assertFalse(walkable.parse_request("preferably near a metro station")["strict"])
        self.assertEqual(walkable.parse_request("near a pharmacy")["amenity"], "pharmacy")

    def test_walking_time_comes_from_routes(self):
        out = self.run_search("supermarket within 10 minutes")
        r = out["results"][0]
        self.assertTrue(r["within_limit"])
        self.assertEqual(r["nearby_amenity"]["walk_seconds"], 420)  # the Routes duration, not a distance estimate

    def test_strict_limit_excludes_long_walks_and_preference_keeps_them(self):
        long_walk = [{"originIndex": 0, "destinationIndex": 0, "duration": "1500s", "distanceMeters": 1900, "condition": "ROUTE_EXISTS"}]
        self.assertEqual(self.run_search("supermarket within 10 minutes", matrix=long_walk)["results"], [])
        kept = self.run_search("preferably a supermarket within 10 minutes", matrix=long_walk)["results"]
        self.assertEqual(len(kept), 1)
        self.assertFalse(kept[0]["within_limit"])

    def test_route_failure_is_not_a_walking_time(self):
        out = self.run_search("preferably a supermarket within 10 minutes", matrix=[{"originIndex": 0, "destinationIndex": 0, "condition": "ROUTE_NOT_FOUND"}])
        r = out["results"][0]
        self.assertEqual(r["route_status"], "unavailable")
        self.assertIsNone(r["nearby_amenity"]["walk_seconds"])

    def test_no_supermarket_found(self):
        out = self.run_search("supermarket within 10 minutes", places=())
        self.assertEqual(out["results"], [])
        self.assertTrue(any("No verified home" in w for w in out["warnings"]))

    def test_dollar_store_tagged_grocery_is_not_a_supermarket(self):
        dollar = {**PLACE, "id": "place-2", "displayName": {"text": "Dollar Store"}, "primaryType": "discount_store"}
        self.assertEqual(self.run_search("supermarket within 10 minutes", places=(dollar,))["results"], [])

    def test_home_without_coordinates_gets_no_walking_badge(self):
        out = self.run_search("preferably a supermarket within 10 minutes", rows=(NO_COORDS,))
        r = out["results"][0]
        self.assertEqual(r["route_status"], "no_coordinates")
        self.assertIsNone(r["nearby_amenity"])
        self.assertTrue(any("no map coordinates" in w for w in out["warnings"]))

    def test_missing_key_shows_setup_guidance(self):
        with patch.dict(os.environ, {"GOOGLE_MAPS_SERVER_API_KEY": ""}):
            out = walkable.search("supermarket within 10 minutes")
        self.assertFalse(out["configured"])
        self.assertIn("WALKABILITY.md", out["warnings"][0])

    def test_unknown_status_and_rent_are_labeled(self):
        out = self.run_search("supermarket within 10 minutes", rows=({**HOME, "monthly_rent": None, "availability": {}},))
        h = out["results"][0]["housing"]
        self.assertEqual(h["monthly_rent_display"], "Contact provider for current rent")
        self.assertIsNone(h["availability_status"])

    def test_outside_northern_virginia_is_refused(self):
        self.assertIn("error", walkable.search("supermarket near Richmond"))

    def test_no_arbitrary_fetches(self):
        self.assertIsNone(walkable.place_photo("../../secrets"))
        self.assertIsNone(walkable.place_photo("https://evil.example/x"))
        self.assertIsNone(walkable.walking_route(38.8, -77.1, "never-returned-by-a-search"))

    def test_key_never_in_response(self):
        out = self.run_search("supermarket within 10 minutes")
        self.assertNotIn("test-key", str(out))


if __name__ == "__main__":
    unittest.main()
