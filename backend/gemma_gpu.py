"""Gemma 4 on our own Cloud Run GPU (Ollama), used before the Gemini API when GEMMA_GPU_URL is set.

The GPU service is private: on Cloud Run this app signs each call with its own identity (an ID token
from the metadata server). Locally, set GEMMA_GPU_TOKEN to `gcloud auth print-identity-token` to try it.
Thinking is off by default, so answers start in seconds; questions with specific needs (pets, furnished, lease length...) let Gemma think them through.
If the GPU is still starting (it scales to zero) or fails, callers fall back to the Gemini API.

Usage: python backend/gemma_gpu.py "What is a housing choice voucher?"
"""
import http.client
import json
import os
import sys
import threading
import time
import urllib.parse

import requests

MODEL = os.environ.get("GEMMA_GPU_MODEL", "gemma4:26b")
FIRST_BYTE_SECONDS = 20  # a cold GPU takes minutes to start; don't make anyone wait for that
# Gemma's window per answer: the prompt plus everything it writes (thinking included) must fit. It must equal
# OLLAMA_CONTEXT_LENGTH on the GPU service (gemma/Dockerfile): a different num_ctx makes Ollama reload the model, and a
# prompt that doesn't fit is silently cut to its last half, losing the rules and the question.
CONTEXT_TOKENS = 16384
THINK_TOKENS, ANSWER_TOKENS = 6000, 900  # most Gemma may write with and without thinking
_token, _lock = {"value": None, "expires": 0.0}, threading.Lock()
_cold_until = 0.0  # after a failed call, skip the GPU briefly instead of waiting on it every time
_ready_at = 0.0  # last time the GPU answered; Cloud Run lets an idle GPU sleep after about 15 minutes
_warm_started, _warm_lock = 0.0, threading.Lock()  # one wake-up call at a time (a cold start takes a few minutes)


def url():
    return os.environ.get("GEMMA_GPU_URL", "").rstrip("/")


def available():
    return bool(url()) and time.time() >= _cold_until


def asleep():
    """True when the GPU probably needs a cold start (minutes), so the page can say it's warming up."""
    return bool(url()) and time.time() - _ready_at > 12 * 60


def prompt_budget(think=True):
    """The longest prompt, in characters, that still fits Gemma's window with room for its answer (and thinking).
    Our prompts are JSON-heavy, about 3 characters a token, so this errs on the safe side."""
    return (CONTEXT_TOKENS - (THINK_TOKENS if think else ANSWER_TOKENS) - 256) * 3


def _mark_ready():
    global _ready_at
    _ready_at = time.time()


def _auth():
    if os.environ.get("GEMMA_GPU_TOKEN"):
        return {"Authorization": f"Bearer {os.environ['GEMMA_GPU_TOKEN']}"}
    with _lock:
        if not _token["value"] or time.time() > _token["expires"]:
            # On Cloud Run, the metadata server hands out an ID token for this service's own identity.
            resp = requests.get("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity",
                                params={"audience": url(), "format": "full"}, headers={"Metadata-Flavor": "Google"}, timeout=5)
            resp.raise_for_status()
            _token["value"] = resp.text.strip()
            _token["expires"] = time.time() + 45 * 60  # ID tokens last an hour
        return {"Authorization": f"Bearer {_token['value']}"}


def _mark_cold(seconds=90):
    global _cold_until
    _cold_until = time.time() + seconds


def stream_parts(prompt, think=False):
    """Yield (is_thought, text) from the GPU as it's written. Raises if the GPU isn't ready, so callers can fall back.
    think=True lets Gemma reason first (for questions with requirements our filters don't cover), with room to check every home."""
    try:
        resp = requests.post(f"{url()}/api/chat", headers=_auth(), stream=True, timeout=(10, FIRST_BYTE_SECONDS),
                             json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": True,
                                   # Thinking shares the token budget with the answer, so it gets plenty of room to check every home.
                                   "think": think, "options": {"temperature": 0.3, "num_ctx": CONTEXT_TOKENS,
                                                               "num_predict": THINK_TOKENS if think else ANSWER_TOKENS}})
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            message = data.get("message") or {}
            _mark_ready()
            if message.get("thinking"):
                yield True, message["thinking"]
            if message.get("content"):
                yield False, message["content"]
            if data.get("done"):
                return
    except Exception as error:
        print(f"Gemma GPU unavailable, using the Gemini API instead: {type(error).__name__}: {str(error)[:200]}", flush=True)
        _mark_cold()
        raise


def stream(prompt, think=False):
    """Yield only the answer text (no thinking) as it's written."""
    for is_thought, text in stream_parts(prompt, think):
        if not is_thought:
            yield text


def ask(prompt):
    return "".join(stream(prompt))


def warm():
    """Wake the GPU (it scales to zero) so it's ready by the first question; True when a wake-up call went out.
    Waits until that call has reached the GPU: on Cloud Run this app's CPU slows to a crawl once it has answered, so a
    call still in a background thread might never be sent. Only one wake-up at a time, and none while the GPU is awake."""
    global _warm_started
    with _warm_lock:
        if not url() or not asleep() or time.time() - _warm_started < 5 * 60:
            return False
        _warm_started = time.time()
    sent = threading.Event()

    def run():
        global _warm_started
        try:
            parts = urllib.parse.urlsplit(url())
            conn = (http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection)(parts.netloc, timeout=300)
            body = json.dumps({"model": MODEL, "prompt": "hi", "stream": False, "think": False,
                               "options": {"num_predict": 1, "num_ctx": CONTEXT_TOKENS}})
            conn.request("POST", parts.path + "/api/generate", body, {"Content-Type": "application/json", **_auth()})
            sent.set()  # the GPU has the call and starts up; the answer (once the model is loaded) can take minutes
            if conn.getresponse().status == 200:
                _mark_ready()
                return
        except Exception:
            pass
        _warm_started = 0.0  # it didn't work, so the next visitor can try again
        sent.set()
    threading.Thread(target=run, daemon=True).start()
    sent.wait(5)
    return True


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if len(sys.argv) < 2 or not url():
        raise SystemExit(__doc__ + "\nSet GEMMA_GPU_URL first.")
    start = time.time()
    for piece in stream(" ".join(sys.argv[1:])):
        print(piece, end="", flush=True)
    print(f"\n[{time.time() - start:.1f}s]")
