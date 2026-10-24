"""Gemma 4 on our own Cloud Run GPU (Ollama), used before the Gemini API when GEMMA_GPU_URL is set.

The GPU service is private: on Cloud Run this app signs each call with its own identity (an ID token
from the metadata server). Locally, set GEMMA_GPU_TOKEN to `gcloud auth print-identity-token` to try it.
Thinking is turned off, so answers start in seconds instead of after a minute of hidden reasoning.
If the GPU is still starting (it scales to zero) or fails, callers fall back to the Gemini API.

Usage: python backend/gemma_gpu.py "What is a housing choice voucher?"
"""
import json
import os
import sys
import threading
import time

import requests

MODEL = os.environ.get("GEMMA_GPU_MODEL", "gemma4:26b")
FIRST_BYTE_SECONDS = 20  # a cold GPU takes minutes to start; don't make anyone wait for that
_token, _lock = {"value": None, "expires": 0.0}, threading.Lock()
_cold_until = 0.0  # after a failed call, skip the GPU briefly instead of waiting on it every time


def url():
    return os.environ.get("GEMMA_GPU_URL", "").rstrip("/")


def available():
    return bool(url()) and time.time() >= _cold_until


def _auth():
    if os.environ.get("GEMMA_GPU_TOKEN"):
        return {"Authorization": f"Bearer {os.environ['GEMMA_GPU_TOKEN']}"}
    with _lock:
        if not _token["value"] or time.time() > _token["expires"]:
            import google.auth.transport.requests
            import google.oauth2.id_token
            _token["value"] = google.oauth2.id_token.fetch_id_token(google.auth.transport.requests.Request(), url())
            _token["expires"] = time.time() + 45 * 60  # ID tokens last an hour
        return {"Authorization": f"Bearer {_token['value']}"}


def _mark_cold(seconds=90):
    global _cold_until
    _cold_until = time.time() + seconds


def stream(prompt):
    """Yield answer text from the GPU as it's written. Raises if the GPU isn't ready, so callers can fall back."""
    try:
        resp = requests.post(f"{url()}/api/chat", headers=_auth(), stream=True, timeout=(10, FIRST_BYTE_SECONDS),
                             json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": True,
                                   "think": False, "options": {"temperature": 0.3, "num_predict": 900}})
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            text = (data.get("message") or {}).get("content")
            if text:
                yield text
            if data.get("done"):
                return
    except Exception:
        _mark_cold()
        raise


def ask(prompt):
    return "".join(stream(prompt))


def warm():
    """Start the GPU in the background (it scales to zero), so the first question doesn't wait for it."""
    if not url():
        return
    def run():
        try:
            requests.post(f"{url()}/api/generate", headers=_auth(), timeout=300,
                          json={"model": MODEL, "prompt": "hi", "stream": False, "think": False, "options": {"num_predict": 1}})
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if len(sys.argv) < 2 or not url():
        raise SystemExit(__doc__ + "\nSet GEMMA_GPU_URL first.")
    start = time.time()
    for piece in stream(" ".join(sys.argv[1:])):
        print(piece, end="", flush=True)
    print(f"\n[{time.time() - start:.1f}s]")
