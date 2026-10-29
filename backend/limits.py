"""Rate limits for the routes that cost money or GPU time (Gemma, Gemini, Google Places/Routes).

Each visitor (by IP address) gets a per-minute and per-day allowance per route group, and each server instance has an
hourly ceiling per group, so one script can't run up the bill or keep the GPU awake and a crowd of them hits a wall.
Counts live in memory, per instance (Cloud Run runs at most 2): a restart forgets them, which is fine for this.

Usage:  @app.post("/api/ask")  @limited("chat")  def ask(): ...
"""
import functools
import ipaddress
import threading
import time
from collections import deque

from flask import jsonify, request

# group: (per IP per minute, per IP per day, per instance per hour)
LIMITS = {
    "chat": (12, 300, 1500),      # Gemma on our GPU, the Gemini API as a fallback
    "sort": (12, 300, 1500),      # the mini Gemma chats above the listings and programs
    "web": (3, 30, 200),          # Gemini + Google Search for live listings
    "places": (30, 600, 4000),    # Places / Routes searches (hotels, walking times, nearby)
    "photos": (120, 3000, 20000),  # Places photos: a result page shows several
    "warm": (4, 60, 300),         # wakes the GPU
    "form": (60, 2000, 20000),    # the find form (no AI, but it may geocode)
}
TOO_MANY = "You've sent a lot of requests in a short time. Please wait a minute and try again, or call 211 for help now."
BUSY = "Clear Home is very busy right now. Please try again in a few minutes, or call 211 for help now."

_lock = threading.Lock()
_hits: dict[tuple, deque] = {}  # (group, ip) -> times in the last day
_instance: dict[str, deque] = {}  # group -> times in the last hour
# Google's load balancers and private hops, skipped when reading X-Forwarded-For from the right.
_PROXIES = [ipaddress.ip_network(n) for n in ("35.191.0.0/16", "130.211.0.0/22", "10.0.0.0/8", "169.254.0.0/16",
                                              "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "::1/128", "fc00::/7", "fe80::/10")]


def client_ip() -> str:
    """The visitor's address. Cloud Run's front end appends the real client to X-Forwarded-For, so read it from the
    right, skipping Google's own hops; anything further left was written by the client and can't be trusted."""
    for part in reversed(request.headers.get("X-Forwarded-For", "").split(",")):
        try:
            ip = ipaddress.ip_address(part.strip())
        except ValueError:
            continue
        if not any(ip in n for n in _PROXIES):
            return str(ip)
    return request.remote_addr or "?"


def _allow(group: str, ip: str, now: float) -> str | None:
    """None when the request may go ahead (and it's counted), else the message to send back."""
    per_minute, per_day, per_hour = LIMITS[group]
    with _lock:
        mine = _hits.setdefault((group, ip), deque())
        while mine and now - mine[0] > 86400:
            mine.popleft()
        everyone = _instance.setdefault(group, deque())
        while everyone and now - everyone[0] > 3600:
            everyone.popleft()
        if len(mine) >= per_day or sum(1 for t in reversed(mine) if now - t < 60) >= per_minute:
            return TOO_MANY
        if len(everyone) >= per_hour:
            return BUSY
        mine.append(now)
        everyone.append(now)
        if len(_hits) > 50_000:  # forget visitors with nothing in the last day, so memory stays small
            for key in [k for k, q in _hits.items() if not q or now - q[-1] > 86400]:
                del _hits[key]
    return None


def limited(group: str):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            ip = client_ip()
            # A teammate's own computer (python backend/app.py, the tests): no proxy header and a loopback address.
            # Cloud Run's front end always adds X-Forwarded-For, so the hosted site is always counted.
            if not request.headers.get("X-Forwarded-For") and ip in ("127.0.0.1", "::1"):
                return fn(*args, **kwargs)
            problem = _allow(group, ip, time.time())
            if problem:
                response = jsonify(error=problem)
                response.status_code = 429
                response.headers["Retry-After"] = "60"
                return response
            return fn(*args, **kwargs)
        return wrapper
    return deco
