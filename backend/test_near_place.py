"""'Something close to walmart': the store is found (or asked about first), and only homes a measured trip away count as close.

Google and Gemma are mocked, so this runs offline. Run: python backend/test_near_place.py
"""
import json
import unittest
from unittest.mock import patch

import advisor
import app as server
import near_place
import nearby

STORE = {"latitude": 37.2296, "longitude": -80.4139}  # a made-up Walmart in Blacksburg
WALMART = {"id": "w1", "displayName": {"text": "Walmart Supercenter"}, "formattedAddress": "1 Test Rd, Blacksburg, VA 24060, USA",
           "location": STORE, "businessStatus": "OPERATIONAL", "types": ["discount_store", "store"]}
OFFICE = {"id": "w2", "displayName": {"text": "Walmart Labs"}, "formattedAddress": "2 Office Park, Blacksburg, VA 24060, USA",
          "location": {"latitude": 37.2300, "longitude": -80.4100}, "businessStatus": "OPERATIONAL", "types": ["corporate_office"]}


def home(id, name, rent, north, seconds):
    """A verified home `north` degrees of latitude from the store, whose walking route takes `seconds` (None: no route)."""
    return {"id": id, "name": name, "type": "affordable_listing", "lat": round(STORE["latitude"] + north, 6), "lon": STORE["longitude"],
            "monthly_rent": rent, "rental_space": "entire_home", "phone": "540-555-0100", "seconds": seconds}


HOMES = [home("cheap", "Cheap Across The Highway", 600, 0.004, 7200),  # 0.3 mi in a straight line, a two-hour walk around
         home("near", "Near The Store", 1400, 0.002, 480),
         home("mid", "Twelve Minutes Away", 900, 0.006, 720),
         home("noroute", "No Route Home", 500, 0.001, None),  # nearest and cheapest, but Google has no walking route
         home("far", "Far Away Farm", 400, 0.2, 600)]  # 14 miles off: never routed, whatever a route would say


class FakeGoogle:
    def __init__(self, places=None, routes_fail=False):
        self.queries, self.modes, self.origins = [], [], []
        self.places, self.routes_fail = places or [WALMART, OFFICE], routes_fail

    def __call__(self, url, body, mask):
        if url == nearby.PLACES_TEXT_URL:
            self.queries.append(body["textQuery"])
            if not any(name.lower() in body["textQuery"].lower() for name in ("walmart", "target")):
                return {"places": [{"displayName": {"text": "Blacksburg"}, "formattedAddress": "Blacksburg, VA", "location": STORE}]}
            return {"places": self.places}
        self.modes.append(body["travelMode"])
        if self.routes_fail:
            raise TimeoutError("routes down")
        rows = []
        for i, origin in enumerate(body["origins"]):
            lat = origin["waypoint"]["location"]["latLng"]["latitude"]
            self.origins.append(lat)
            h = next(h for h in HOMES if h["lat"] == lat)
            for j, _ in enumerate(body["destinations"]):
                seconds = h["seconds"] if body["travelMode"] == "WALK" else round(h["seconds"] or 600) // 4
                rows.append({"originIndex": i, "destinationIndex": j, "condition": "ROUTE_NOT_FOUND"} if h["seconds"] is None else
                            {"originIndex": i, "destinationIndex": j, "duration": f"{seconds}s", "distanceMeters": seconds, "condition": "ROUTE_EXISTS"})
        return rows


def homes(text, profile=None):
    homes.seen = text
    return [dict(h) for h in HOMES]


def events(response):
    return [json.loads(line[6:]) for line in response.get_data(as_text=True).split("\n\n") if line.startswith("data: ")]


@patch.object(near_place, "_homes", side_effect=homes)
@patch.object(nearby, "_key", return_value="test")
class NearPlaceTests(unittest.TestCase):
    def setUp(self):
        near_place._cache.clear()
        nearby._cache.clear()
        advisor._cache.clear()

    def answer(self, question, google=None, profile=None, history=None):
        self.setUp()  # each call is a fresh lookup, not the cached one from the line before
        google = google or FakeGoogle()
        with patch.object(nearby, "_post", side_effect=google):
            return near_place.answer(question, profile or {}, history or []), google

    def test_a_chain_with_no_town_asks_which_store_before_any_lookup(self, *_):
        with patch.object(nearby, "_post", side_effect=AssertionError("no lookups before we know which store")):
            text = near_place.answer("give me something close to walmart", {}, [])
            broad = near_place.answer("close to walmart in northern virginia", {}, [])
        self.assertIsInstance(text, advisor.Instant)
        self.assertIn("Which Walmart, or which city?", text)
        self.assertIn("10–15 minute walk what you mean by close", text)  # "close" isn't silently defined
        self.assertIn("many Walmart stores", broad)

    def test_the_chat_asks_without_gemma(self, *_):
        client = server.app.test_client()
        with patch("advisor.stream_gemma", side_effect=AssertionError("Gemma should not be needed")), patch("hotels._key", return_value=""), \
                patch.object(nearby, "_post", side_effect=AssertionError("no lookups yet")):
            got = events(client.post("/api/ask/stream", json={"question": "give me something close to walmart"}))
        self.assertIn("Which Walmart, or which city?", next(e["text"] for e in got if e["kind"] == "answer"))
        self.assertEqual(next(e["text"] for e in got if e["kind"] == "engine"), advisor.Instant.engine)

    def test_cheap_two_hour_walk_loses_to_a_nearby_home(self, *_):
        for question in ("give me something close to walmart in blacksburg", "cheapest place close to walmart in blacksburg"):
            with self.subTest(question):
                text, _ = self.answer(question)
                self.assertTrue(text.startswith("The Walmart nearest Blacksburg is Walmart Supercenter, 1 Test Rd, Blacksburg"), text)
                self.assertIn("didn't give a time, so I used up to 15 minutes on foot", text)  # the default is said out loud
                self.assertIn("**Near The Store**: 8 min walk", text)
                self.assertIn("**Twelve Minutes Away**: 12 min walk", text)
                self.assertNotIn("Cheap Across The Highway", text)
        text, _ = self.answer("give me something close to walmart in blacksburg")
        self.assertLess(text.index("Near The Store"), text.index("Twelve Minutes Away"))  # quickest trip first
        text, _ = self.answer("cheapest place close to walmart in blacksburg")
        self.assertLess(text.index("Twelve Minutes Away"), text.index("Near The Store"))  # cheapest first, but only among close ones

    def test_an_explicit_time_limit_is_enforced(self, *_):
        text, _ = self.answer("homes within a 10 minute walk of walmart in blacksburg")
        self.assertIn("within a 10-minute walk of it", text)
        self.assertNotIn("give a time", text)
        self.assertIn("Near The Store", text)
        self.assertNotIn("Twelve Minutes Away", text)
        text, _ = self.answer("a 5 minute walk to walmart in blacksburg")
        self.assertIn("None of the verified homes that fit your choices is within a 5-minute walk", text)
        self.assertIn("longer than your limit", text)
        self.assertIn("**Near The Store**: 8 min walk", text.split("longer than your limit")[1])
        self.assertNotIn("Cheap Across The Highway", text)  # a two-hour walk isn't even an "almost"

    def test_failed_and_unknown_routes_are_never_close(self, *_):
        text, google = self.answer("give me something close to walmart in blacksburg")
        self.assertNotIn("No Route Home", text)
        self.assertIn("no walking route for 1 nearby home", text)
        self.assertNotIn(HOMES[4]["lat"], google.origins)  # far homes aren't even routed
        text, _ = self.answer("give me something close to walmart in blacksburg", FakeGoogle(routes_fail=True))
        self.assertIn("didn't answer just now", text)
        self.assertIn("not confirmed as close", text)
        self.assertNotIn("**", text)  # nothing is presented as a result (no cards)
        self.assertNotIn("min walk", text)
        with patch.object(nearby, "_key", return_value=""):
            self.assertIn("isn't set up", near_place.answer("close to walmart in blacksburg", {}, []))

    def test_offices_under_the_brand_are_not_stores(self, *_):
        text, _ = self.answer("close to walmart in blacksburg")
        self.assertNotIn("Walmart Labs", text)
        text, _ = self.answer("close to walmart in blacksburg", FakeGoogle(places=[OFFICE]))
        self.assertIn("couldn't find a Walmart near Blacksburg", text)
        self.assertIn(advisor.PLACE_MARK, text)

    def test_the_town_can_come_from_the_find_form_or_earlier_in_the_chat(self, *_):
        _, google = self.answer("close to walmart", profile={"location": "Blacksburg"})
        self.assertIn("Walmart near blacksburg, VA", google.queries)
        earlier = [{"role": "user", "text": "cheap rooms in blacksburg"}, {"role": "assistant", "text": "Here are rooms in Blacksburg."}]
        text, google = self.answer("anything close to walmart?", history=earlier)
        self.assertIn("Near The Store", text)

    def test_the_reply_to_which_store_keeps_the_whole_request(self, *_):
        ask = str(near_place.answer("give me something close to walmart under 1500", {}, []))
        history = [{"role": "user", "text": "give me something close to walmart under 1500"}, {"role": "assistant", "text": ask}]
        merged = advisor.with_context("blacksburg, 10 minutes", history)
        text, google = self.answer(merged, history=history)
        self.assertIn("within a 10-minute walk of it", text)
        self.assertTrue(any("blacksburg" in q.lower() for q in google.queries))
        self.assertIn("under 1500", homes.seen)  # the budget from the first message still filters the homes

    def test_follow_up_about_that_store_keeps_the_place(self, *_):
        first, _ = self.answer("close to walmart in blacksburg")
        history = [{"role": "user", "text": "close to walmart in blacksburg"}, {"role": "assistant", "text": str(first)}]
        text, _ = self.answer("what about a 25 minute walk from that store?", history=history)
        self.assertIn("within a 25-minute walk of it", text)
        self.assertIn("Walmart Supercenter", text)
        self.assertNotIn("Cheap Across The Highway", text)  # two hours is still not 25 minutes

    def test_drive_and_bus_change_the_route_mode(self, *_):
        text, google = self.answer("a 10 minute drive to walmart in blacksburg")
        self.assertEqual(google.modes, ["DRIVE"])
        self.assertIn("within a 10-minute drive of it", text)
        _, google = self.answer("20 minutes by bus to walmart in blacksburg")
        self.assertEqual(google.modes, ["TRANSIT"])
        self.assertEqual(near_place._trip("walk instead (earlier in this chat: a 10 minute drive to walmart)")[0], "WALK")  # newest words win

    def test_a_named_street_picks_those_stores_and_is_not_richmond(self, *_):
        on_hwy = [{**WALMART, "id": "a", "formattedAddress": "6303 Richmond Hwy, Alexandria, VA 22306, USA"},
                  {**WALMART, "id": "b", "displayName": {"text": "Walmart"}, "formattedAddress": "7910 Richmond Hwy, Alexandria, VA 22306, USA",
                   "location": {"latitude": 37.2200, "longitude": -80.4139}}]
        text, google = self.answer("walking distance from the walmart on richmond hwy", FakeGoogle(places=on_hwy))
        self.assertEqual(google.queries, ["Walmart richmond hwy, VA"])
        self.assertTrue(text.startswith('The 2 Walmart stores matching "richmond hwy"'), text)
        text, _ = self.answer("walking distance from the walmart at 7910 richmond hwy", FakeGoogle(places=on_hwy))
        self.assertTrue(text.startswith("Walmart, 7910 Richmond Hwy"), text)

    def test_names_spellings_and_other_places_are_read(self, *_):
        for question, chain in [("near Wal-Mart", "Walmart"), ("close to wallmart", "Walmart"), ("close to walmrat", "Walmart"),
                                ("walking distance from the walmart on richmond hwy", "Walmart"), ("next to a target", "Target"),
                                ("near home depo", "Home Depot"), ("by the kroger", "Kroger"), ("close to trader joes", "Trader Joe's")]:
            with self.subTest(question):
                self.assertEqual(near_place.read(question)["chain"], chain)
        self.assertEqual(near_place.read("something close to Inova Fairfax Hospital")["place"], "Inova Fairfax Hospital")
        self.assertEqual(near_place.read("close to fair oaks mall")["place"], "fair oaks mall")  # lowercase still a named place
        for question in ["something close to campus", "near my office", "near aldie", "close to 3 people", "near the end of the month",
                         "I got kicked out, anything near walmart tonight?", "near my office at 1800 Tysons Blvd"]:
            with self.subTest(question):
                self.assertIsNone(near_place.read(question))  # other paths (campus question, commute answer, shelters) handle these

    def test_other_needs_go_to_gemma_with_only_the_measured_homes(self, *_):
        client, seen = server.app.test_client(), {}
        def fake(prompt, thoughts=False, think=False):
            seen["prompt"] = prompt
            yield False, "**Near The Store** allows cats."
        with patch("advisor.stream_gemma", side_effect=fake), patch("hotels._key", return_value=""), patch.object(nearby, "_post", side_effect=FakeGoogle()):
            got = events(client.post("/api/ask/stream", json={"question": "something close to walmart in blacksburg that allows pets"}))
        self.assertIn("Finding the Walmart", next(e["text"] for e in got if e["kind"] == "status"))
        prompt = seen["prompt"]
        self.assertIn("Place: The Walmart nearest Blacksburg is Walmart Supercenter", prompt)
        self.assertIn("within a 15-minute walk of", prompt)
        resources = json.loads(prompt.split("for the requested area):\n", 1)[1].split("\n", 1)[0])  # the line after the label
        self.assertEqual({r["name"] for r in resources}, {"Near The Store", "Twelve Minutes Away"})
        self.assertTrue(all("walk_minutes_to_walmart" in r for r in resources))

    def test_without_gemma_the_fallback_keeps_the_store_and_limit(self, *_):
        def broken(prompt, thoughts=False, think=False):
            raise RuntimeError("billing")
            yield
        with patch("advisor.stream_gemma", side_effect=broken), patch.object(nearby, "_post", side_effect=FakeGoogle()):
            got = list(advisor.stream_ask("something close to walmart in blacksburg that allows pets"))
        text = next(t for kind, t in got if kind == "fallback")
        self.assertIn("Walmart Supercenter", text)
        self.assertIn("Near The Store", text)
        self.assertNotIn("Cheap Across The Highway", text)

    def test_cards_link_directions_to_the_same_store(self, *_):
        text = near_place.with_directions("**Union Blacksburg** is a 5 min walk.", {"union blacksburg": "https://www.google.com/maps/dir/?api=1&x=1"})
        card = next(c for c in advisor.cards_for(text) if c["name"] == "Union Blacksburg")
        self.assertEqual(card["directions"], "https://www.google.com/maps/dir/?api=1&x=1")
        self.assertNotIn("directions", next(iter(advisor.cards_for("**Union Blacksburg**"))))


if __name__ == "__main__":
    unittest.main()
