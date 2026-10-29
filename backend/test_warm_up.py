"""While the Gemma GPU wakes up, a fast Gemini model answers at once (labeled as such, never saved as Gemma's answer),
the GPU is woken in the background, and an awake GPU still answers everything itself.

Google and the GPU are faked, so this runs offline. Run: python backend/test_warm_up.py
"""
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import advisor
import gemma_gpu
import matcher
import sorter


class FakeModels:
    """The Gemini API: records which model each call used; models in `fail` raise before any words."""
    def __init__(self, fail=()):
        self.calls, self.fail = [], set(fail)

    def generate_content_stream(self, model, contents, config=None):
        self.calls.append(model)
        if model in self.fail:
            raise RuntimeError("503 UNAVAILABLE")
        part = SimpleNamespace(text=f"Answer from {model}.", thought=False)
        yield SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])

    def generate_content(self, model, contents, config=None):
        self.calls.append(model)
        if model in self.fail:
            raise RuntimeError("503 UNAVAILABLE")
        return SimpleNamespace(text=f'{{"order": ["a"], "note": "Answer from {model}."}}')


class WarmUpTests(unittest.TestCase):
    def setUp(self):
        advisor._cache.clear()
        sorter._program_cache.clear()
        self.models, self.woken = FakeModels(), threading.Event()
        self.patches = [patch.dict("os.environ", {"GEMMA_GPU_URL": "https://gpu.example"}),
                        patch.object(gemma_gpu, "_cold_until", 0.0),
                        patch.object(gemma_gpu, "warm", side_effect=lambda: self.woken.set()),
                        patch.object(matcher, "_get_client", return_value=SimpleNamespace(models=self.models))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def asleep(self):
        return patch.object(gemma_gpu, "_ready_at", 0.0)

    def test_a_sleeping_gpu_means_gemini_answers_at_once_and_the_gpu_is_woken(self):
        with self.asleep(), patch.object(gemma_gpu, "stream_parts", side_effect=AssertionError("don't wait on a sleeping GPU")):
            got = list(matcher.stream_gemma("q", thoughts=True, think=True))
        self.assertEqual(got[0], ("status", matcher.WAKING_NOTE))
        self.assertEqual(got[1], ("engine", matcher.FAST_ENGINE))
        self.assertEqual(got[2], (False, f"Answer from {matcher.FAST_MODEL}."))
        self.assertEqual(self.models.calls, [matcher.FAST_MODEL])
        self.assertTrue(self.woken.wait(2))  # the wake-up call goes out in the background
        self.assertIn("Gemma 4 26B", matcher.FAST_ENGINE)  # the page's "Gemma answered" touches still apply

    def test_an_awake_gpu_answers_itself(self):
        with patch.object(gemma_gpu, "_ready_at", time.time()), patch.object(gemma_gpu, "stream_parts", return_value=iter([(False, "Gemma here.")])):
            got = list(matcher.stream_gemma("q", thoughts=True))
        self.assertIn((False, "Gemma here."), got)
        self.assertTrue(got[0][0] == "engine" and "Cloud Run L4 GPU" in got[0][1])
        self.assertEqual(self.models.calls, [])
        self.assertFalse(self.woken.is_set())

    def test_if_gemini_fails_gemma_on_the_gemini_api_still_answers(self):
        self.models.fail.add(matcher.FAST_MODEL)
        with self.asleep():
            got = list(matcher.stream_gemma("q", thoughts=True))
        self.assertEqual(self.models.calls, [matcher.FAST_MODEL, matcher.MODEL])
        self.assertIn(("engine", f"Gemma 4 26B ({matcher.MODEL}) via the Gemini API"), got)
        self.assertTrue(any(kind == "status" and "up to a minute" in text for kind, text in got if isinstance(kind, str)))

    def test_without_a_gpu_nothing_changes(self):
        with patch.dict("os.environ", {"GEMMA_GPU_URL": ""}):
            list(matcher.stream_gemma("q", thoughts=True))
        self.assertEqual(self.models.calls, [matcher.MODEL])

    def test_quick_asks_get_gemini_while_checks_wait_for_gemma(self):
        with self.asleep():
            answer = matcher.ask_gemma("q")
        self.assertIsInstance(answer, matcher.StandIn)
        self.assertEqual(self.models.calls, [matcher.FAST_MODEL])
        self.models.calls.clear()
        with self.asleep(), patch.object(gemma_gpu, "ask", side_effect=RuntimeError("cold")):
            answer = matcher.ask_gemma("q", quick=False)  # freshness checks: never the stand-in
        self.assertNotIsInstance(answer, matcher.StandIn)
        self.assertEqual(self.models.calls, [matcher.MODEL])

    def test_stand_in_answers_are_not_saved_as_gemmas(self):
        def reply(engine):
            return lambda prompt, thoughts=False, think=False: iter([("engine", engine), (False, "Call **ARHA**.")])
        with patch("advisor.stream_gemma", side_effect=reply(matcher.FAST_ENGINE)):
            list(advisor.stream_ask("How do vouchers work in Alexandria?"))
        self.assertEqual(advisor._cache, {})
        with patch("advisor.stream_gemma", side_effect=reply("Gemma 4 26B (gemma4:26b) on our own Cloud Run L4 GPU")):
            list(advisor.stream_ask("How do vouchers work in Alexandria?"))
        self.assertEqual(len(advisor._cache), 1)

    def test_startup_warm_up_still_saves_gemmas_answers(self):
        with self.asleep(), patch.object(gemma_gpu, "ask", side_effect=RuntimeError("cold")), patch.object(advisor, "EXAMPLES", ["What documents do I need to apply?"]), \
                patch.object(advisor.threading, "Thread", side_effect=lambda target, daemon: SimpleNamespace(start=target)), patch.object(advisor.time, "sleep"):
            advisor.warm_examples()  # nobody is waiting on these, so they wait for Gemma instead of the stand-in
        self.assertNotIn(matcher.FAST_MODEL, self.models.calls)
        self.assertEqual(list(advisor._cache), ["what documents do i need to apply?"])

    def test_sorting_says_which_model_sorted(self):
        ids = [r["id"] for r in sorter.filter_catalog(sorter.load_catalog()) if r.get("type") in ("affordable_listing", "rental_listing")][:5]
        with self.asleep(), patch("sorter._ask", side_effect=lambda q, cards: sorter._reply(matcher.StandIn('{"order": ["%s"], "note": "Cheapest."}' % cards[0]["id"]))):
            got = sorter.sort("cheapest first", ids)
        self.assertEqual(got["engine"], matcher.FAST_ENGINE)
        with patch("sorter.ask_gemma", return_value='{"order": ["x"], "note": "n", "engine": "made up"}'):
            self.assertEqual(sorter._ask("q", [{"id": "x"}])["engine"], "Gemma 4")  # a model can't set the label


if __name__ == "__main__":
    unittest.main()
