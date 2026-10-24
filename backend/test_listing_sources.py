"""Listing links must point at the right property and be labeled by where they go.

Run: python backend/test_listing_sources.py
"""
import collections
import json
import unittest
from unittest.mock import patch

import source_audit
from catalog import RESOURCES_PATH

LRG_PAGE = "https://www.fcrha.org/properties/little-river-glen/1"
LRG_IV_PAGE = "https://www.fcrha.org/properties/little-river-glen-iv/1"


class FakeResponse:
    def __init__(self, html, status=200):
        self.text, self.status_code, self.headers = html, status, {"Content-Type": "text/html; charset=utf-8"}


class ListingSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(RESOURCES_PATH.read_text())
        cls.listings = [r for r in cls.rows if r.get("type") == "affordable_listing"]
        cls.by_id = {r["id"]: r for r in cls.rows}

    def test_little_river_glen_links_to_its_own_property_page(self):
        lrg = self.by_id["little-river-glen-one-bedroom"]
        self.assertEqual(lrg["source_url"], LRG_PAGE)
        self.assertEqual(lrg["source_kind"], "official_property_page")
        self.assertIn("Included", lrg["utilities"])
        self.assertTrue(lrg["amenities"])
        self.assertIn("separate", lrg["notes"])  # assisted living and Little River Glen IV are separate

    def test_little_river_glen_and_glen_iv_stay_distinct(self):
        lrg, iv = self.by_id["little-river-glen-one-bedroom"], self.by_id["redbud-glen-one-bedroom"]
        self.assertNotEqual(lrg["community"], iv["community"])
        self.assertEqual(iv["source_url"], LRG_IV_PAGE)
        self.assertNotIn(LRG_IV_PAGE, {s["url"] for s in lrg.get("sources", [])} | {lrg["source_url"]})
        self.assertNotIn(LRG_PAGE, {s["url"] for s in iv.get("sources", [])} | {iv["source_url"]})

    def test_shared_links_are_labeled_as_directories(self):
        communities = collections.defaultdict(set)
        for r in self.listings:
            communities[r["source_url"]].add((r.get("community") or r["name"]).casefold())
        for r in self.listings:
            with self.subTest(r["id"]):
                self.assertIn(r.get("source_kind"), source_audit_kinds())
                if len(communities[r["source_url"]]) > 1:
                    self.assertEqual(r["source_kind"], "official_directory")

    def test_general_page_that_only_mentions_a_property_is_not_accepted(self):
        page = "<title>Renter Resources | City of Alexandria</title><h1>Renter Resources</h1><p>Witter Place Apartments, 2 Witter Place ...</p>"
        with patch.object(source_audit.requests, "get", return_value=FakeResponse(page)):
            self.assertFalse(source_audit.page_matches("https://www.alexandriava.gov/renter-resources", "Witter Place Apartments", "2 Witter Place"))

    def test_similarly_named_building_is_not_accepted(self):
        page = "<title>The Terraces at Arlington View West | AHC</title><h1>The Terraces at Arlington View West</h1><p>1420 S Rolfe</p>"
        with patch.object(source_audit.requests, "get", return_value=FakeResponse(page)):
            self.assertFalse(source_audit.page_matches("https://ahcommunities.org/x", "Arlington View Terrace", "1429 S Rolfe St"))

    def test_property_page_titled_with_the_community_is_accepted(self):
        page = "<title>Little River Glen | FCRHA</title><h1>Little River Glen</h1><p>120 one-bedroom apartments</p>"
        with patch.object(source_audit.requests, "get", return_value=FakeResponse(page)):
            self.assertTrue(source_audit.page_matches(LRG_PAGE, "Little River Glen", "4001 Barker Court"))

    def test_blocked_pages_are_not_verified(self):
        with patch.object(source_audit.requests, "get", return_value=FakeResponse("Just a moment...", status=403)):
            self.assertFalse(source_audit.page_matches("https://www.littleriverglenapts.com/", "Little River Glen", "4001 Barker Court"))


def source_audit_kinds():
    return {"official_property_page", "owner_property_page", "property_website", "official_directory"}


if __name__ == "__main__":
    unittest.main()
