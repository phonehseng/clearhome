"""Hotels and motels for someone who needs a place tonight: cheapest first, only real rooms in our area, always a Maps link.

Google is mocked, so this runs offline. Run: python backend/test_hotels.py
"""
import json
import unittest
from unittest.mock import patch

import advisor
import app as server
import hotels


def place(name, level=None, kind="hotel", status="OPERATIONAL", lat=38.88, lon=-77.10, **extra):
    p = {"displayName": {"text": name}, "primaryType": kind, "primaryTypeDisplayName": {"text": kind.title()}, "businessStatus": status,
         "formattedAddress": f"{name} St, Arlington, VA", "location": {"latitude": lat, "longitude": lon}, **extra}
    if level:
        p["priceLevel"] = level
    return p


GOOGLE = {"places": [
    place("Grand Hotel", "PRICE_LEVEL_EXPENSIVE"),
    place("Budget Inn", "PRICE_LEVEL_INEXPENSIVE", kind="motel", nationalPhoneNumber="(703) 555-0100", websiteUri="https://budget.example"),
    place("No Price Suites", kind="extended_stay_hotel", websiteUri="http://insecure.example"),
    place("Middle Hotel", "PRICE_LEVEL_MODERATE", rating=4.1, userRatingCount=812),
    place("Second Cheap Motel", "PRICE_LEVEL_INEXPENSIVE", kind="motel"),
    place("Closed Motel", "PRICE_LEVEL_INEXPENSIVE", kind="motel", status="CLOSED_PERMANENTLY"),
    place("Lakeside Campground", "PRICE_LEVEL_INEXPENSIVE", kind="campground"),
    place("Richmond Motel", "PRICE_LEVEL_INEXPENSIVE", kind="motel", lat=37.54, lon=-77.43),  # outside Northern Virginia
]}


def events(response):
    return [json.loads(line[6:]) for line in response.get_data(as_text=True).split("\n\n") if line.startswith("data: ")]


class HotelTests(unittest.TestCase):
    def setUp(self):
        hotels._cache.clear()
        advisor._cache.clear()
        self.key = patch("hotels._key", return_value="test-key")
        self.key.start()
        self.addCleanup(self.key.stop)

    def test_cheapest_first_and_only_open_rooms_in_the_area(self):
        with patch("hotels._post", return_value=GOOGLE) as post:
            found = hotels.near("Arlington")
        self.assertEqual([h["name"] for h in found["hotels"]], ["Budget Inn", "Second Cheap Motel", "Middle Hotel", "No Price Suites", "Grand Hotel"])
        self.assertEqual(found["place"], "Arlington, VA")  # not Arlington, Texas
        self.assertIn("hotels%20near%20Arlington%2C%20VA", found["search_url"])
        self.assertEqual(post.call_args[0][1]["includedType"], "lodging")
        budget, suites = found["hotels"][0], found["hotels"][3]
        self.assertEqual((budget["phone"], budget["website"], budget["price"]), ("(703) 555-0100", "https://budget.example", "$ · Inexpensive"))
        self.assertNotIn("website", suites)  # only https links reach the page
        self.assertNotIn("_rank", budget)

    def test_answers_are_cached_but_failures_are_not(self):
        with patch("hotels._post", side_effect=OSError("down")):
            self.assertEqual(hotels.near("Reston")["hotels"], [])
        with patch("hotels._post", return_value=GOOGLE) as post:
            hotels.near("Reston"); hotels.near("Reston")
        self.assertEqual(post.call_count, 1)

    def test_without_a_maps_key_only_the_google_maps_link(self):
        with patch("hotels._key", return_value=""), patch("hotels._post") as post:
            found = hotels.near("Blacksburg")
        post.assert_not_called()
        self.assertEqual((found["hotels"], found["place"]), ([], "Blacksburg, VA"))
        self.assertTrue(found["search_url"].startswith("https://www.google.com/maps/search/"))

    def test_api_refuses_places_outside_our_area(self):
        client = server.app.test_client()
        with patch("hotels._post", return_value=GOOGLE):
            ok = client.post("/api/hotels", json={"place": "Arlington"})
            outside = client.post("/api/hotels", json={"place": "Richmond"})
            junk = client.post("/api/hotels", json=[1, 2])
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.get_json()["hotels"][0]["name"], "Budget Inn")
        self.assertEqual(outside.status_code, 400)
        self.assertEqual(junk.status_code, 200)  # no place: the whole region
        self.assertEqual(junk.get_json()["area"], "Northern Virginia")

    def test_only_questions_about_tonight_get_hotels(self):
        self.assertEqual(hotels.place_for("Where can I sleep tonight?", {"location": "Reston"}), "Reston")
        self.assertEqual(hotels.place_for("Somewhere safe to sleep tonight in Arlington", {"location": "Blacksburg"}), "Arlington County")
        self.assertEqual(hotels.place_for("I have nowhere to sleep tonight"), "Northern Virginia")
        self.assertEqual(hotels.place_for("cheap motels in Blacksburg"), "Blacksburg")
        self.assertIsNone(hotels.place_for("How do vouchers work in Alexandria?", {"location": "Alexandria"}))
        self.assertIsNone(hotels.place_for("somewhere to sleep tonight in Richmond"))

    def test_chat_sends_hotels_after_the_answer(self):
        client = server.app.test_client()
        with patch("advisor.stream_gemma", return_value=iter([(False, "Call 211 tonight.")])), patch("hotels._post", return_value=GOOGLE):
            got = events(client.post("/api/ask/stream", json={"question": "I have nowhere to sleep tonight", "profile": {"location": "Arlington"}}))
        kinds = [e["kind"] for e in got]
        self.assertEqual(kinds[-2:], ["hotels", "done"])
        self.assertEqual(got[-2]["text"]["hotels"][0]["name"], "Budget Inn")
        with patch("advisor.stream_gemma", return_value=iter([(False, "Call **ARHA**.")])), patch("hotels._post") as post:
            got = events(client.post("/api/ask/stream", json={"question": "How do vouchers work in Alexandria?"}))
        self.assertNotIn("hotels", [e["kind"] for e in got])
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
