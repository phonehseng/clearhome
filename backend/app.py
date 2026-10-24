"""Small web server: serves the page in frontend/ and the /api/match endpoint.

Run:  python backend/app.py      then open http://localhost:8000
Set INCLUDE_UNVERIFIED=1 to also use placeholder entries while testing.
"""
import os

from flask import Flask, jsonify, request, send_from_directory

from matcher import find_help

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
app = Flask(__name__, static_folder=None)


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.post("/api/match")
def match():
    message = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not message:
        return jsonify(error="Please describe your situation."), 400
    if len(message) > 2000:
        return jsonify(error="Please keep it under 2000 characters."), 400
    try:
        filters, answer = find_help(message, include_unverified=bool(os.getenv("INCLUDE_UNVERIFIED")))
    except Exception:
        return jsonify(error="Something went wrong. Please try again, or call 211 for help."), 500
    return jsonify(filters=filters, answer=answer)


if __name__ == "__main__":
    app.run(port=8000, debug=True)
