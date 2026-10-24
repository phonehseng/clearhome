"""The live chat: progress first, then Gemma's words; catalog answers when Gemma can't reply; bad input is refused.

Gemma and Google are mocked, so this runs offline. Run: python backend/test_chat_stream.py
"""
import json
import unittest
from unittest.mock import patch

import advisor
import app as server


def events(response):
    return [json.loads(line[6:]) for line in response.get_data(as_text=True).split("\n\n") if line.startswith("data: ")]


class ChatStreamTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        advisor._cache.clear()

    def test_progress_then_streamed_words(self):
        with patch("advisor.stream_gemma", return_value=iter([(True, "Looking at voucher programs in Alexandria\n"), (False, "Call "), (False, "**ARHA**.")])):
            got = events(self.client.post("/api/ask/stream", json={"question": "How do vouchers work in Alexandria?"}))
        self.assertEqual(got[0]["kind"], "status")
        self.assertEqual("".join(e["text"] for e in got if e["kind"] == "chunk"), "Call **ARHA**.")
        self.assertEqual(got[-1]["kind"], "done")

    def test_named_places_become_cards(self):
        cards = advisor.cards_for("Call **Arlington Housing Choice Voucher Program (AHCVP)** or try **West Wood Oaks**.")
        self.assertEqual([c["name"] for c in cards][:1], ["Arlington Housing Choice Voucher Program (AHCVP, formerly Section 8)"])
        self.assertIn("West Wood Oaks", [c["name"] for c in cards])
        self.assertEqual(advisor.cards_for("No names here."), [])

    def test_catalog_answer_when_gemma_only_thinks(self):
        with patch("advisor.stream_gemma", return_value=iter([(True, "thinking...\n")])):
            got = events(self.client.post("/api/ask/stream", json={"question": "Who helps with back rent in Alexandria?"}))
        self.assertEqual([e["kind"] for e in got][-2:], ["fallback", "cards"])
        self.assertTrue(got[-1]["text"])  # the catalog answer's programs come back as cards

    def test_catalog_answer_when_gemma_billing_fails(self):
        def broken(prompt, thoughts=False):
            raise RuntimeError("402 RESOURCE_EXHAUSTED: Your prepayment credits are depleted")
            yield
        with patch("advisor.stream_gemma", side_effect=broken):
            got = events(self.client.post("/api/ask/stream", json={"question": "Who helps with back rent in Alexandria?"}))
        fallback = next(e for e in got if e["kind"] == "fallback")["text"]
        self.assertIn("billing", fallback)
        self.assertIn("Alexandria", fallback)  # real local rent-help programs, not apartments

    def test_shelter_question_is_never_answered_with_apartments(self):
        with patch("advisor.stream_gemma", return_value=iter([(False, "Call 211 tonight.")])):
            got = events(self.client.post("/api/ask/stream", json={"question": "I was kicked out by my landlord, where can I sleep tonight?",
                                                                    "profile": {"location": "Arlington", "tonight": True}}))
        self.assertNotIn("answer", [e["kind"] for e in got])  # no instant "homes near" list
        self.assertIn("211", "".join(e["text"] for e in got if isinstance(e["text"], str)))

    def test_bad_input_is_refused_not_crashed(self):
        for body in ({"question": 123}, {"question": ""}, {"question": "x" * 2000}, [1, 2]):
            with self.subTest(body):
                self.assertEqual(self.client.post("/api/ask/stream", json=body).status_code, 400)
        ok = self.client.post("/api/ask", json={"question": "near my office", "history": {"bad": 1}, "profile": {"budget": True, "household": float("inf")}})
        self.assertEqual(ok.status_code, 200)

    def test_income_zero_still_shows_programs(self):
        data = self.client.post("/api/options", json={"location": "Arlington", "income": 0}).get_json()
        self.assertTrue(data["programs_relevant"])

    def test_rent_help_question_picks_rent_help_first(self):
        rows = advisor._records("Who helps with back rent in Alexandria?")
        self.assertIn(rows[0]["type"], {"rental_assistance", "legal_aid"})

    def test_room_question_includes_student_rooms_within_budget(self):
        rows = advisor._records("A room near Virginia Tech under $700")
        rooms = [r for r in rows if r["type"] == "rental_listing"]
        self.assertTrue(rooms)
        self.assertTrue(all(r.get("monthly_rent") is None or r["monthly_rent"] <= 700 for r in rows))


if __name__ == "__main__":
    unittest.main()
