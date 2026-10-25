"""Walking-time questions are measured, not guessed; unusual requirements get walking facts and a brief Gemma think.

Google and Gemma are mocked or absent, so this runs offline. Run: python backend/test_walk_and_needs.py
"""
import json
import unittest
from unittest.mock import MagicMock, patch

import advisor
import app as server
import gemma_gpu
import nearby

EARLIER = ("Here are rooms in Blacksburg:\n• **1711 Apartments — Unit 04** · $565\n• **Maple Ridge Townhomes**\n"
           "• **Terrace View — 3Ax1.5 T3** · $865\n• **Union Blacksburg — D2** · $1,210.79")
HISTORY = [{"role": "user", "text": "cheap rooms in blacksburg"}, {"role": "assistant", "text": EARLIER}]


class WalkTests(unittest.TestCase):
    def setUp(self):
        nearby._cache.clear()
        advisor._cache.clear()

    @patch.object(nearby, "_key", return_value="")
    def test_follow_up_about_these_listings_is_measured(self, _):
        text = nearby.answer("are these at least 13 minutes away walk from virginia tech campus", {}, HISTORY)
        self.assertTrue(text.startswith("Yes, all 4 are at least a 13-minute walk from Virginia Tech."), text)
        for name in ("1711 Apartments", "Maple Ridge Townhomes", "Terrace View", "Union Blacksburg"):
            self.assertIn(f"**{name}**", text)
        self.assertIn("estimated", text)  # no Google key: labeled as an estimate

    @patch.object(nearby, "_key", return_value="test")
    def test_google_walking_times_are_used_when_available(self, _):
        def fake_post(url, body, mask):
            self.assertEqual(body["travelMode"], "WALK")
            return [{"originIndex": i, "duration": f"{600 + 60 * i}s", "condition": "ROUTE_EXISTS"} for i in range(len(body["origins"]))]
        with patch.object(nearby, "_post", side_effect=fake_post):
            text = nearby.answer("is 1711 Apartments within a 20 min walk of virginia tech?", {})
        self.assertTrue(text.startswith("Yes, it is within a 20-minute walk of Virginia Tech."), text)
        self.assertIn("about 10 min walk, ", text)
        self.assertIn("from Google Maps", text)

    @patch.object(nearby, "_key", return_value="test")
    def test_fresh_question_filters_by_the_walk(self, _):
        def fake_post(url, body, mask):  # 6, 9, 12... minutes: only the first few fit
            return [{"originIndex": i, "duration": f"{360 + 180 * i}s", "condition": "ROUTE_EXISTS"} for i in range(len(body["origins"]))]
        with patch.object(nearby, "_post", side_effect=fake_post):
            text = nearby.answer("rooms within a 15 minute walk of virginia tech", {})
        self.assertTrue(text.startswith("Reviewed homes within a 15-minute walk of Virginia Tech"), text)
        minutes = [int(m) for m in __import__("re").findall(r"about (\d+) min walk", text)]
        self.assertTrue(minutes and all(m <= 15 for m in minutes))

    @patch.object(nearby, "_key", return_value="")
    def test_straight_line_estimates_never_count_as_within_a_walk(self, _):
        text = nearby.answer("rooms within a 15 minute walk of virginia tech", {})
        self.assertTrue(text.startswith("Google walking routes aren't available right now, so I can't verify"), text)
        self.assertNotIn("✓", text)
        self.assertLessEqual(text.count("\n- "), 8)

    def test_walking_with_other_requirements_goes_to_gemma(self):
        q = ("i am in blacksburg and i want housing that is furnished for 1 year, under 1000 a month and at least "
             "a 13 minute walk from campus, i do not want to pay more than 1 year lease")
        self.assertIsNone(nearby.answer(q, {}, []))
        self.assertEqual(advisor.extra_needs(q), ["walking time", "furnished", "lease length"])
        self.assertEqual(advisor.walk_target(q), ("Virginia Tech", 37.2284, -80.4234, 13, True))

    def test_everyday_questions_do_not_trigger_thinking(self):
        for q in ["2 bedroom in arlington under 1500 a month", "I need to move in 2 months", "How do I qualify for Section 8?",
                  "cheap rooms in blacksburg", "I walk my dog every morning"]:
            with self.subTest(q):
                self.assertIsNone(nearby.answer(q, {}, []) if "walk" in q else None)
        for q in ["2 bedroom in arlington under 1500 a month", "I need to move in 2 months", "cheap rooms in blacksburg",
                  "Is the tax credit apartment in Reston open?"]:
            self.assertEqual(advisor.extra_needs(q), [])

    def test_specific_situations_let_gemma_think(self):
        self.assertEqual(advisor.extra_needs("Furnished room near VT that allows my emotional support cat"), ["furnished", "pets"])
        self.assertEqual(advisor.extra_needs("A roommate setup, move-in by Jan 5, no smoking"), ["roommates", "move-in date", "smoking"])
        self.assertEqual(advisor.extra_needs("Apartments with no credit check on the ground floor"), ["floor access", "screening rules"])


class ThinkingTests(unittest.TestCase):
    def setUp(self):
        advisor._cache.clear()

    @patch.object(nearby, "_key", return_value="")
    def test_unusual_requirements_add_walk_times_and_think(self, _):
        seen = {}
        def fake_stream(prompt, thoughts=False, think=False):
            seen.update(prompt=prompt, think=think)
            return iter([(False, "None meet all of them.")])
        q = "furnished room in blacksburg under 1000, at least a 13 minute walk from campus"
        with patch("advisor.stream_gemma", side_effect=fake_stream):
            server.app.test_client().post("/api/ask/stream", json={"question": q}).get_data()
        self.assertTrue(seen["think"])
        self.assertIn("walk_minutes_to_virginia_tech", seen["prompt"])
        self.assertIn("They asked for at least 13 minutes", seen["prompt"])
        self.assertIn('"furnished":true', seen["prompt"])  # Gemma can now see furnished

    def test_plain_questions_stay_fast(self):
        seen = {}
        def fake_stream(prompt, thoughts=False, think=False):
            seen["think"] = think
            return iter([(False, "Call 211.")])
        with patch("advisor.stream_gemma", side_effect=fake_stream):
            server.app.test_client().post("/api/ask/stream", json={"question": "How do vouchers work in Alexandria?"}).get_data()
        self.assertFalse(seen["think"])

    def test_gpu_passes_thinking_through_separately(self):
        lines = [json.dumps({"message": {"thinking": "Checking walk times"}}).encode(),
                 json.dumps({"message": {"content": "Terrace View fits."}}).encode(), json.dumps({"done": True}).encode()]
        resp = MagicMock(iter_lines=lambda: iter(lines))
        with patch.dict("os.environ", {"GEMMA_GPU_URL": "https://gpu.example", "GEMMA_GPU_TOKEN": "t"}), \
                patch.object(gemma_gpu.requests, "post", return_value=resp) as post:
            parts = list(gemma_gpu.stream_parts("q", think=True))
            answer = gemma_gpu.ask("q")
        self.assertEqual(parts, [(True, "Checking walk times"), (False, "Terrace View fits.")])
        self.assertEqual(answer, "Terrace View fits.")
        self.assertTrue(post.call_args_list[0].kwargs["json"]["think"])
        self.assertFalse(post.call_args_list[1].kwargs["json"]["think"])


if __name__ == "__main__":
    unittest.main()
