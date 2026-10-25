"""Scheduled listing upkeep: Gemini finds new listings and they're only saved when the source page backs every fact;
listings still offered are renewed and gone ones taken down. The mini Gemma chat only re-sorts what's on screen.

Gemini, Gemma, web pages and the geocoder are mocked, so this runs offline. Run: python backend/test_discover.py
"""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import app as server
import discover
import freshness
import sorter
from catalog import filter_catalog, load_catalog

PAGE = ("Maple Commons Apartments. 1200 Example Street, Falls Church, VA 22046. Two bedroom homes from $1,450 per month. "
        "Income limits apply: households earning up to 60% of area median income. Now leasing; apply online.")
FOUND = {"community": "Maple Commons Apartments", "address": "1200 Example Street", "city": "Falls Church", "kind": "affordable",
         "space": "entire_home", "plan": "Two bedroom", "bedrooms": 2, "rent": 1450, "status": "leasing",
         "program": "60% of area median income", "source_url": "https://maplecommons.example.com/floorplans"}
CHECKED = {"listed": True, "community": "Maple Commons Apartments", "address": "1200 Example Street, Falls Church, VA 22046",
           "rent": 1450, "status": "leasing", "program": "up to 60% of area median income",
           "quotes": {"community": "Maple Commons Apartments", "address": "1200 Example Street, Falls Church, VA 22046",
                      "rent": "from $1,450 per month", "program": "households earning up to 60% of area median income"},
           "evidence": "The page says the community is now leasing."}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.resources = self.dir / "resources.json"
        self.resources.write_text(Path(discover.RESOURCES_PATH).read_text(encoding="utf-8"), encoding="utf-8")
        self.queue = self.dir / "candidates.json"
        self.queue.write_text(json.dumps({"candidates": [], "rejected": []}))
        self.review = self.dir / "listing_review.json"
        self.review.write_text(json.dumps({"decisions": {}}))
        for target, path in (("discover.RESOURCES_PATH", self.resources), ("discover.CANDIDATES_PATH", self.queue),
                             ("discover.REVIEW_PATH", self.review), ("sources.CANDIDATES_PATH", self.queue)):
            p = patch(target, path)
            p.start()
            self.addCleanup(p.stop)
        for target in ("discover.time.sleep",):
            p = patch(target)
            p.start()
            self.addCleanup(p.stop)

    def run_with(self, found, checked, page=PAGE, publish=True, point=(38.882, -77.171)):
        with patch("discover.research", return_value=found), patch("discover._page_text", return_value=page), \
                patch("discover.self_check", side_effect=lambda item, text: discover_self_check(item, text, checked)), \
                patch("geocode.lookup", return_value=point):
            return discover.run(["Falls Church City"], publish=publish, log=lambda *_: None)

    def test_a_find_backed_by_its_own_page_goes_live_flagged(self):
        summary = self.run_with([FOUND], CHECKED)
        self.assertEqual(summary["Falls Church City"]["published"], 1)
        rows = json.loads(self.resources.read_text(encoding="utf-8"))
        record = next(r for r in rows if r.get("community") == "Maple Commons Apartments")
        self.assertEqual((record["monthly_rent"], record["jurisdiction"], record["verified"]), (1450, "Falls Church City", True))
        self.assertIn("Not yet reviewed by a person", record["verification_method"])
        self.assertEqual(json.loads(self.review.read_text())["decisions"][record["id"]]["state"], "flagged")
        self.assertTrue(any(r["id"] == record["id"] for r in filter_catalog(load_catalog(self.resources))))  # really on the site

    def test_listing_sites_and_queue_only_runs_never_publish(self):
        aggregator = dict(FOUND, source_url="https://www.apartments.com/maple-commons-falls-church-va/abc123/")
        self.assertEqual(self.run_with([aggregator], CHECKED)["Falls Church City"]["queued"], 1)
        self.assertEqual(self.run_with([dict(FOUND, community="Maple Commons West")], dict(CHECKED, community="Maple Commons West",
                         quotes=dict(CHECKED["quotes"], community="Maple Commons West")), page=PAGE + " Maple Commons West.",
                         publish=False)["Falls Church City"]["queued"], 1)
        rows = json.loads(self.resources.read_text(encoding="utf-8"))
        self.assertFalse(any("Maple Commons" in str(r.get("community")) for r in rows))
        self.assertEqual(len(json.loads(self.queue.read_text())["candidates"]), 2)

    def test_made_up_quotes_are_caught(self):
        fake = dict(CHECKED, quotes=dict(CHECKED["quotes"], rent="from $950 per month"), rent=950)
        facts = discover_self_check(FOUND, PAGE, fake)
        self.assertIsNone(facts["rent"])  # $950 isn't on the page, so no rent is published
        self.assertIsNone(discover_self_check(FOUND, PAGE, dict(CHECKED, quotes=dict(CHECKED["quotes"], community="Oak Ridge Homes"))))

    def test_known_places_are_skipped_and_outside_addresses_wait(self):
        known = next(r for r in json.loads(self.resources.read_text(encoding="utf-8")) if r.get("community"))
        self.assertEqual(self.run_with([dict(FOUND, community=known["community"])], CHECKED)["Falls Church City"]["skipped"], 1)
        self.assertEqual(self.run_with([FOUND], CHECKED, point=(36.85, -75.98))["Falls Church City"]["queued"], 1)  # Virginia Beach

    def test_rotation_moves_on_each_run(self):
        with patch("discover.STATE_PATH", self.dir / "state.json"):
            first, _, following = discover.next_areas(2)
            (self.dir / "state.json").write_text(json.dumps({"next": following}))
            second, _, _ = discover.next_areas(2)
        self.assertEqual(len(set(first) | set(second)), 4)


_real_self_check = discover.self_check


def discover_self_check(item, page, reply):
    """The real self_check (quote matching and all), with Gemini's reply supplied."""
    response = type("Response", (), {"text": json.dumps(reply)})()
    client = type("Client", (), {"models": type("Models", (), {"generate_content": staticmethod(lambda **_: response)})()})()
    with patch("discover._client", return_value=client):
        return _real_self_check(item, page)


class RenewalTests(unittest.TestCase):
    def test_still_offered_is_renewed_only_with_a_real_quote(self):
        today = date.today()
        row = {"id": "x-1", "type": "rental_listing", "name": "Elm Court — Room", "source_url": "https://elmcourt.example.com/rooms",
               "availability": {"status": "leasing", "checked_on": (today - timedelta(days=6)).isoformat(),
                                "review_due": (today + timedelta(days=1)).isoformat(), "evidence": "old"}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "resources.json"
            path.write_text(json.dumps([row, dict(row, id="x-2")]))
            page = "Elm Court rooms: private bedrooms now leasing for fall."
            verdicts = iter([("listed", "private bedrooms now leasing for fall"), ("listed", "rooms available right now")])
            with patch("freshness.RESOURCES_PATH", path), patch("freshness._page_text", return_value=page), \
                    patch("freshness._judge", side_effect=lambda *_: next(verdicts)), patch("freshness.time.sleep"):
                results = dict(freshness.check(force=True, limit=10))
            saved = {r["id"]: r for r in json.loads(path.read_text())}
        self.assertEqual(results, {"x-1": "renewed", "x-2": "listed"})  # the second quote isn't on the page
        self.assertEqual(saved["x-1"]["availability"]["review_due"], (today + timedelta(days=7)).isoformat())
        self.assertEqual(saved["x-2"]["availability"]["review_due"], (today + timedelta(days=1)).isoformat())

    def test_soonest_due_first_within_the_limit(self):
        today = date.today()
        rows = [{"id": f"r{n}", "type": "affordable_listing", "name": f"R{n}", "source_url": f"https://p{n}.example.com",
                 "availability": {"status": "leasing", "checked_on": today.isoformat(), "review_due": (today + timedelta(days=n)).isoformat()}}
                for n in (5, 1, 3)]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "resources.json"
            path.write_text(json.dumps(rows))
            with patch("freshness.RESOURCES_PATH", path), patch("freshness._page_text", return_value=""), \
                    patch("freshness._judge", return_value=("unclear", "")), patch("freshness.time.sleep"):
                self.assertEqual([i for i, _ in freshness.check(force=True, limit=2)], ["r1", "r3"])


class SortChatTests(unittest.TestCase):
    def setUp(self):
        self.ids = [r["id"] for r in filter_catalog(load_catalog()) if r.get("type") in ("affordable_listing", "rental_listing")]

    def test_only_listings_on_screen_come_back_in_gemmas_order(self):
        pick = self.ids[5]
        with patch("sorter.MAX_CANDIDATES", 10_000), patch("sorter.ask_gemma", return_value='```json\n{"order": ["made-up-id", "%s"], "note": "This one is cheapest."}\n```' % pick):
            out = sorter.sort("cheapest first", self.ids)
        self.assertEqual((out["order"], out["note"], out["engine"]), ([pick], "This one is cheapest.", "Gemma 4"))

    def test_busy_gemma_falls_back_to_the_words(self):
        with patch("sorter.ask_gemma", side_effect=RuntimeError("busy")):
            out = sorter.sort(sorter.SAMPLE, self.ids)
        rows = {r["id"]: r for r in load_catalog()}
        self.assertTrue(out["order"] and all("Blacksburg" in str(rows[i].get("city")) for i in out["order"][:4]))
        self.assertIn("busy", out["note"])

    def test_api_checks_its_input(self):
        client = server.app.test_client()
        self.assertEqual(client.post("/api/listings/sort", json={"question": "", "ids": self.ids[:3]}).status_code, 400)
        self.assertEqual(client.post("/api/listings/sort", json={"question": "rooms", "ids": "nope"}).status_code, 400)
        with patch("sorter.ask_gemma", return_value='{"order": ["%s"], "note": "Closest first."}' % self.ids[0]):
            ok = client.post("/api/listings/sort", json={"question": "rooms near campus", "ids": self.ids[:20]})
        self.assertEqual(ok.get_json()["order"], [self.ids[0]])


if __name__ == "__main__":
    unittest.main()
