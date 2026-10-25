"""Follow-up questions in the chat: asked only when a detail would change the answer, answered with buttons or typing,
remembered for the conversation (newer answers win), and never in the way of a general question or an emergency.

Gemma and Google are mocked, so this runs offline. Run: python backend/test_clarifier.py
"""
import json
import unittest
from unittest.mock import patch

import advisor
import app as server
import clarifier as c


def events(response):
    return [json.loads(line[6:]) for line in response.get_data(as_text=True).split("\n\n") if line.startswith("data: ")]


def talk(*messages, profile=None):
    """Run messages through the clarifier like the page does. A (label, [choice ids]) tuple is a button answer."""
    state, out = c.load_state({}), []
    for m in messages:
        reply = None
        if isinstance(m, tuple):
            m, picks = m
            reply = {"id": state["pending"]["id"], "choices": picks}
        out.append(c.resolve(m, state, profile, reply))
    return out, state


class DecisionTests(unittest.TestCase):
    def test_vague_request_asks_what_kind_of_help(self):
        (asked, _), = talk("I need somewhere to live")[0]
        self.assertEqual(asked.question["field"], "help")
        self.assertEqual([x["id"] for x in asked.question["choices"]], ["rental", "tonight", "rent_help"])
        self.assertTrue(asked.question["unsure"])
        self.assertFalse(asked.question["multi"])

    def test_detailed_request_goes_straight_to_an_answer_unchanged(self):
        for text in ("An entire one-bedroom home in Blacksburg under $1,200 a month", "Rooms near Virginia Tech under $700",
                     "Affordable 1-bedroom apartments in Arlington?", "Shelter tonight in Arlington", "Section 8 waitlists in Fairfax"):
            (asked, request), = talk(text)[0]
            self.assertIsNone(asked, text)
            self.assertEqual(request, text)  # nothing repeated back, so saved answers to the example buttons still apply

    def test_general_questions_get_answers_not_a_questionnaire(self):
        for text in ("What is a housing voucher?", "How do I qualify for Section 8?", "What documents do I need to apply?",
                     "I need help with my landlord", "Which voucher waitlists are open right now?"):
            self.assertIsNone(talk(text)[0][0][0], text)

    def test_emergencies_get_help_right_away(self):
        (asked, _), = talk("I need a shelter tonight")[0]
        self.assertEqual(asked.question["field"], "area")  # where they are, beside the help, not instead of it
        for part in ("911", "211"):
            self.assertIn(part, str(asked))
        self.assertIsNone(talk("I need a shelter tonight", profile={"location": "Arlington", "tonight": True})[0][0][0])
        self.assertIsNone(talk("I'm behind on rent and got an eviction notice")[0][0][0])
        self.assertIsNone(talk("I need somewhere to live", profile={"tonight": True})[0][0][0])

    def test_guided_rental_flow_asks_one_thing_at_a_time_then_answers_with_everything(self):
        out, state = talk("I need somewhere to live", ("Find a rental", ["rental"]), ("Blacksburg", ["blacksburg"]), ("Under $1,000", ["1000"]))
        self.assertEqual([a.question["field"] for a, _ in out[:3]], ["help", "area", "budget"])
        self.assertEqual([x["id"] for x in out[2][0].question["choices"]][:2], ["600", "800"])  # Blacksburg budgets, not NoVA's
        asked, request = out[3]
        self.assertIsNone(asked)
        for part in ("I want to find a rental", "in Blacksburg", "under $1000"):
            self.assertIn(part, request)
        self.assertTrue(advisor.housing_search(request))
        rows = advisor._records(request)
        self.assertTrue(rows and all(r["type"] in ("affordable_listing", "rental_listing") for r in rows))
        self.assertTrue(all(r.get("monthly_rent") is None or r["monthly_rent"] <= 1000 for r in rows))
        self.assertEqual(state["answers"], {"help": "rental", "area": "blacksburg", "budget": 1000})
        self.assertIsNone(state["pending"])

    def test_tonight_and_rent_help_paths(self):
        out, _ = talk("I need somewhere to live", ("Somewhere safe tonight", ["tonight"]), ("Arlington", ["arlington"]))
        self.assertIn("911", str(out[1][0]))
        self.assertIn("tonight", out[2][1])
        self.assertEqual(server.hotels.place_for(out[2][1]), "Arlington County")  # the hotels list follows the answer
        out, state = talk("Rent help in Alexandria", ("Rent I'm behind on, Utility bills", ["back_rent", "utilities"]))
        self.assertTrue(out[0][0].question["multi"])
        self.assertIn("behind on rent", out[1][1])
        self.assertIn("utility bills", out[1][1])

    def test_skip_and_not_sure_stay_unknown(self):
        out, state = talk("I need an apartment", ("Not sure", ["unsure"]), ("Skip", ["skip"]))
        self.assertEqual(state["answers"], {"area": "unsure", "budget": "skip"})  # not a guessed city or a $0 budget
        request = out[-1][1]
        self.assertIn("broad results", request)
        self.assertIn("don't assume one", request)
        out, state = talk("I need help", ("Not sure", ["unsure"]))
        self.assertIsNone(out[1][0])
        self.assertIn("explain the main options", out[1][1])

    def test_typed_answers_count_like_buttons(self):
        out, state = talk("Apartments in Arlington", "1500")
        self.assertEqual(out[0][0].question["field"], "budget")
        self.assertEqual(state["answers"]["budget"], 1500)
        out, state = talk("I need an apartment", "Reston")
        self.assertEqual(state["answers"]["area"], "reston")
        self.assertEqual(out[1][0].question["field"], "budget")
        out, state = talk("I need an apartment", "Richmond")  # outside the area: say so and ask again
        self.assertEqual(out[1][0].question["field"], "area")
        self.assertIn("only covers", str(out[1][0]))
        self.assertNotIn("area", state["answers"])

    def test_corrections_override_and_answers_are_remembered(self):
        out, state = talk("Apartments in Arlington", ("Under $1,600", ["1600"]), "actually Alexandria")
        self.assertIsNone(out[2][0])
        self.assertIn("Alexandria", out[2][1])
        self.assertNotIn("Arlington", out[2][1])
        self.assertIn("under $1600", out[2][1])
        out, state = talk("Apartments in Arlington", ("Under $1,600", ["1600"]), "studios under 1200")
        self.assertEqual(state["answers"]["budget"], 1200)  # a newer budget replaces the older one
        self.assertIn("in Arlington", out[2][1])  # the area is still remembered
        self.assertEqual(advisor.BUDGET_ANY.search(out[2][1]).group(1), "1200")
        # The campus question: a typed reply keeps the whole request, and its correction wins.
        reported = "i need something close to campus under 1000 and they need accessable with pets and is a 2 person"
        out, state = talk(reported, "Virginia Tech, actually under 1200", "per person")
        self.assertIn(advisor.CLARIFY_MARK, str(out[0][0]))
        self.assertIn("$1,200", str(out[1][0]))  # then total or per person, about the corrected budget
        self.assertEqual(advisor.BUDGET_ANY.search(out[2][1]).group(1), "1200")
        self.assertIn("accessable with pets", out[2][1])
        self.assertIn("per person", out[2][1])

    def test_campus_question_then_total_or_per_person(self):
        reported = "i need something close to campus under 1000 and they need accessable with pets and is a 2 person"
        out, _ = talk(reported, ("Virginia Tech (Blacksburg)", ["virginia tech"]), ("Total for everyone", ["total"]))
        self.assertEqual([x["id"] for x in out[0][0].question["choices"]], ["virginia tech", "george mason"])
        self.assertIn("for 2 people", str(out[0][0]))
        self.assertEqual(out[1][0].question["field"], "basis")
        request = out[2][1]
        self.assertIn("close to Virginia Tech", request)
        self.assertIn("total for everyone", request)
        self.assertTrue(all(r["type"] in ("affordable_listing", "rental_listing") for r in advisor._records(request)))

    def test_conflicting_places_are_asked_about(self):
        out, state = talk("Apartments in Blacksburg or Arlington", ("Arlington", ["arlington"]), ("Skip", ["skip"]))
        self.assertEqual([x["id"] for x in out[0][0].question["choices"]], ["blacksburg", "arlington"])
        self.assertIn("Blacksburg and Arlington", str(out[0][0]))
        self.assertIn("Apartments in Arlington", out[2][1])
        self.assertNotIn("Blacksburg", out[2][1])
        # An older answer doesn't silently settle a new conflict.
        _, state = talk("Apartments in Reston", ("Under $1,600", ["1600"]), "rooms in Blacksburg or Arlington")
        self.assertNotIn("area", state["answers"])

    def test_at_most_three_questions_per_request(self):
        out, state = talk("I need somewhere to live", ("Find a rental", ["rental"]), ("Blacksburg", ["blacksburg"]), ("Skip", ["skip"]))
        self.assertIsNone(out[3][0])  # a fourth (room or whole home) would be one too many
        self.assertEqual(len(state["asked"]), 3)


class StateTests(unittest.TestCase):
    def test_unknown_fields_bad_values_and_forged_questions_are_dropped(self):
        state = c.load_state({"answers": {"area": "atlantis", "budget": "lots", "admin": True, "help": "rental", "situation": ["eviction", "rm -rf"],
                                          "basis": "total", "budget2": 5}, "asked": ["area", "nope"], "request": "x" * 5000,
                              "pending": {"id": "<img onerror=1>", "field": "area"}})
        self.assertEqual(state["answers"], {"help": "rental", "basis": "total"})
        self.assertEqual(state["asked"], ["area"])
        self.assertEqual(len(state["request"]), 1500)
        self.assertIsNone(state["pending"])
        for junk in (None, [], "state", 7, {"answers": [1]}, {"pending": {"id": "q_area_0123abcd", "field": "budget"}}):
            self.assertEqual(c.load_state(junk)["pending"], None)

    def test_replies_must_answer_the_open_question_with_its_choices(self):
        _, state = talk("I need somewhere to live")
        qid = state["pending"]["id"]
        with self.assertRaises(c.Stale):
            c.resolve("Find a rental", state, reply={"id": "q_help_00000000", "choices": ["rental"]})
        with self.assertRaises(ValueError):
            c.resolve("Rent", state, reply={"id": qid, "choices": ["mansion"]})
        with self.assertRaises(ValueError):
            c.resolve("Both", state, reply={"id": qid, "choices": ["rental", "tonight"]})  # one answer, not several
        c.resolve("Find a rental", state, reply={"id": qid, "choices": ["rental"]})
        with self.assertRaises(c.Stale):  # the same click twice
            c.resolve("Find a rental", state, reply={"id": qid, "choices": ["rental"]})

    def test_a_new_request_keeps_area_and_budget_but_not_the_kind_of_help(self):
        _, state = talk("I need somewhere to live", ("Find a rental", ["rental"]), ("Arlington", ["arlington"]), ("Under $1,600", ["1600"]))
        asked, request = c.resolve("What is a housing voucher?", state)
        self.assertIsNone(asked)
        self.assertEqual(request, "What is a housing voucher?")  # nothing added to a general question
        self.assertEqual(state["answers"], {"area": "arlington", "budget": 1600})

    def test_other_modules_can_ask_with_the_builder(self):
        asked = c.question("place", "Which Walmart, or which city?",
                           [("Walmart, Christiansburg", "Walmart in Christiansburg"), ("<script>", "bad"), ("Walmart, Fairfax", "Walmart in Fairfax")])
        self.assertEqual([x["id"] for x in asked.question["choices"]], ["Walmart, Christiansburg", "Walmart, Fairfax"])
        self.assertTrue(c.QID.fullmatch(asked.question["id"]))
        with self.assertRaises(KeyError):
            c.question("anything_goes", "?", [("a", "A")])
        state = c.load_state({})
        c.record(state, asked, "apartments close to walmart")
        c.resolve("Walmart in Christiansburg", state, reply={"id": asked.question["id"], "choices": ["Walmart, Christiansburg"]})
        self.assertIn("near Walmart, Christiansburg", c.compose(state["request"], state["answers"]))


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        advisor._cache.clear()

    def post(self, **body):
        return self.client.post("/api/ask/stream", json=body)

    def test_question_arrives_as_data_with_the_state_and_without_gemma_cards_or_hotels(self):
        with patch("advisor.stream_gemma", side_effect=AssertionError("Gemma should not be needed")), \
                patch("hotels.lookup_later", side_effect=AssertionError("no hotels while asking where")):
            got = events(self.post(question="I need a place to stay", chat={}))
        kinds = [e["kind"] for e in got]
        self.assertEqual(kinds, ["state", "engine", "answer", "question"])
        q = got[3]["text"]
        self.assertEqual(q["field"], "help")
        self.assertEqual(got[0]["text"]["pending"], {"id": q["id"], "field": "help"})
        self.assertEqual(got[2]["text"], "What kind of help do you need first?")

    def test_answers_carry_through_to_gemma(self):
        chat = events(self.post(question="I need somewhere to live", chat={}))[0]["text"]
        got = events(self.post(question="Find a rental", chat=chat, reply={"id": chat["pending"]["id"], "choices": ["rental"]}))
        chat = got[0]["text"]
        self.assertEqual(got[-1]["text"]["field"], "area")
        got = events(self.post(question="Blacksburg", chat=chat, reply={"id": chat["pending"]["id"], "choices": ["blacksburg"]}))
        chat = got[0]["text"]
        seen = {}
        def fake(prompt, thoughts=False, think=False):
            seen["prompt"] = prompt
            yield False, "Here are rooms in Blacksburg."
        with patch("advisor.stream_gemma", side_effect=fake), patch("hotels._key", return_value=""):
            got = events(self.post(question="Under $800", chat=chat, reply={"id": chat["pending"]["id"], "choices": ["800"]},
                                   profile={"location": "Northern Virginia"}))
        self.assertIn("in Blacksburg", seen["prompt"])
        self.assertIn("under $800", seen["prompt"])
        self.assertIn("rental housing search", seen["prompt"])
        self.assertNotIn("looking in Northern Virginia", seen["prompt"])  # the chat's newer area answer wins over the form's
        self.assertEqual(got[-1]["kind"], "done")
        self.assertEqual(got[0]["text"]["answers"], {"help": "rental", "area": "blacksburg", "budget": 800})

    def test_stale_and_bad_replies_are_refused(self):
        chat = events(self.post(question="I need somewhere to live", chat={}))[0]["text"]
        reply = {"id": chat["pending"]["id"], "choices": ["rental"]}
        newer = events(self.post(question="Find a rental", chat=chat, reply=reply))[0]["text"]
        self.assertEqual(self.post(question="Find a rental", chat=newer, reply=reply).status_code, 409)  # an old question's button
        self.assertEqual(self.post(question="Mansion", chat=newer, reply={"id": newer["pending"]["id"], "choices": ["mansion"]}).status_code, 400)
        self.assertEqual(self.post(question="x", chat="garbage", reply="garbage").status_code, 409)

    def test_a_question_asked_in_words_still_gets_its_reply_merged(self):
        seen = []
        def fake(question, profile=None, history=None):  # near_place.py's "Which Walmart, or which city?"
            seen.append(question)
            return advisor.Instant(f"Which Walmart, {advisor.PLACE_MARK}" if len(seen) == 1 else "Homes near the Walmart.")
        first = "give me something close to walmart under 1500"
        with patch("near_place.answer", side_effect=fake), patch("hotels._key", return_value=""):
            got = events(self.post(question=first, chat={}))
            self.assertEqual(seen, [first])  # no area question first: the store names its own place
            history = [{"role": "user", "text": first}, {"role": "assistant", "text": next(e["text"] for e in got if e["kind"] == "answer")}]
            events(self.post(question="blacksburg", chat=got[0]["text"], history=history))
        self.assertEqual(seen[1], f"blacksburg (earlier in this chat: {first})")

    def test_pages_without_chat_state_work_as_before(self):
        with patch("advisor.stream_gemma", return_value=iter([(False, "A voucher helps pay rent.")])):
            got = events(self.post(question="I need somewhere to live"))
        self.assertNotIn("question", [e["kind"] for e in got])
        self.assertNotIn("state", [e["kind"] for e in got])
        body = self.client.post("/api/ask", json={"question": "I need somewhere to live", "chat": {}}).get_json()
        self.assertEqual(body["question"]["field"], "help")
        self.assertEqual(body["chat"]["pending"]["field"], "help")


if __name__ == "__main__":
    unittest.main()
