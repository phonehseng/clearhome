"""Rental searches with several requirements: understood despite typos, asked about when "campus" is unclear, and
answered from housing listings with every requirement kept, across follow-ups.

Gemma and Google are mocked, so this runs offline. Run: python backend/test_chat_intent.py
"""
import json
import unittest
from unittest.mock import patch

import advisor
import app as server

REPORTED = "i need something close to campus under 1000 and they need accessable with pets and is a 2 person"
LISTINGS = {"affordable_listing", "rental_listing"}


def events(response):
    return [json.loads(line[6:]) for line in response.get_data(as_text=True).split("\n\n") if line.startswith("data: ")]


class IntentTests(unittest.TestCase):
    def setUp(self):
        advisor._cache.clear()

    def test_requirements_are_read_despite_typos(self):
        self.assertTrue(advisor.housing_search(REPORTED))
        self.assertEqual(advisor.household_size(REPORTED), 2)
        self.assertTrue(advisor.ACCESSIBLE.search(REPORTED))  # "accessable"
        self.assertIn("pets", advisor.extra_needs(REPORTED))
        for text, people in [("two people", 2), ("me and my partner", 2), ("a 3-person household", 3), ("a 2 bedroom apartment", None)]:
            self.assertEqual(advisor.household_size(text), people, text)  # people, never bedrooms

    def test_unclear_campus_gets_one_question_that_keeps_everything(self):
        text = advisor.clarify(REPORTED)
        for part in ("near campus", "under $1,000 a month", "accessible", "allows pets", "for 2 people", advisor.CLARIFY_MARK,
                     "Virginia Tech", "George Mason", "total monthly budget or per person"):
            self.assertIn(part, text)
        self.assertNotIn("shelter", text.lower())
        # Already clear: a named campus, a place, or the find form's area.
        self.assertIsNone(advisor.clarify(REPORTED.replace("campus", "Virginia Tech")))
        self.assertIsNone(advisor.clarify(REPORTED + " in Blacksburg"))
        self.assertIsNone(advisor.clarify(REPORTED, {"location": "Blacksburg"}))
        self.assertIsNone(advisor.clarify("I need a shelter tonight near campus"))  # emergencies are never held up

    def test_the_reply_keeps_the_request_and_finds_homes_in_budget(self):
        history = [{"role": "user", "text": REPORTED}, {"role": "assistant", "text": str(advisor.clarify(REPORTED))}]
        merged = advisor.with_context("Virginia Tech, total for both of us", history)
        self.assertIn("Virginia Tech", merged)
        self.assertIn("accessable with pets", merged)
        self.assertIsNone(advisor.clarify(merged))
        rows = advisor._records(merged, history)
        self.assertTrue(rows)
        self.assertTrue(all(r["type"] in LISTINGS for r in rows))
        self.assertTrue(all(r.get("monthly_rent") is None or r["monthly_rent"] <= 1000 for r in rows))
        self.assertTrue(all("Blacksburg" in str(r.get("region") or r.get("jurisdiction")) or r.get("jurisdiction") == "Montgomery County" for r in rows))
        # A correction in the reply wins over what it replaces.
        self.assertEqual(advisor.BUDGET_ANY.search(advisor.with_context("Virginia Tech, actually under 1200", history)).group(1), "1200")

    def test_a_rental_search_after_shelter_talk_is_still_a_rental_search(self):
        shelter = [{"role": "user", "text": "where is a shelter tonight"}, {"role": "assistant", "text": "Call 211 for shelter."}]
        self.assertEqual({r["type"] for r in advisor._records("2 bedroom apartment in Arlington under 1500", shelter)} - LISTINGS, set())
        self.assertIn("emergency_shelter", {r["type"] for r in advisor._records("I need a shelter tonight in Arlington")})

    def test_chat_asks_first_without_calling_gemma(self):
        client = server.app.test_client()
        with patch("advisor.stream_gemma", side_effect=AssertionError("Gemma should not be needed")), patch("hotels._key", return_value=""):
            got = events(client.post("/api/ask/stream", json={"question": REPORTED}))
        answer = next(e["text"] for e in got if e["kind"] == "answer")
        self.assertIn(advisor.CLARIFY_MARK, answer)
        self.assertEqual(next(e["text"] for e in got if e["kind"] == "engine"), advisor.Instant.engine)

    def test_follow_up_sends_gemma_the_whole_request_and_homes_only(self):
        client = server.app.test_client()
        seen = {}
        def fake(prompt, thoughts=False, think=False):
            seen.update(prompt=prompt, think=think)
            yield False, "Here are rooms near Virginia Tech."
        history = [{"role": "user", "text": REPORTED}, {"role": "assistant", "text": str(advisor.clarify(REPORTED))}]
        with patch("advisor.stream_gemma", side_effect=fake), patch("hotels._key", return_value=""):
            events(client.post("/api/ask/stream", json={"question": "Virginia Tech, total for both of us", "history": history}))
        prompt = seen["prompt"]
        self.assertTrue(seen["think"])
        for part in ("rental housing search", "Household: 2 people", "not a bedroom count", "accessible field is true", "confirm the pet policy",
                     "verified matches", "accessable with pets"):
            self.assertIn(part, prompt)
        resources = json.loads(prompt.rsplit("\n", 1)[-1])
        self.assertTrue(resources and all(r["type"] in LISTINGS for r in resources))


if __name__ == "__main__":
    unittest.main()
