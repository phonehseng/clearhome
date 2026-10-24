"""Small web server: serves the page in frontend/ and the /api endpoints.

Run:  python backend/app.py      then open http://localhost:8000
Set INCLUDE_UNVERIFIED=1 to also use placeholder entries while testing.
"""
import os

from flask import Flask, jsonify, request, send_from_directory

from extract_text import extract_text
from lease_checker import check_listing, explain_lease
from matcher import find_help
from redact import redact

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB uploads


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
    message, _ = redact(message)
    try:
        filters, answer = find_help(message, include_unverified=bool(os.getenv("INCLUDE_UNVERIFIED")))
    except Exception:
        return jsonify(error="Something went wrong. Please try again, or call 211 for help."), 500
    return jsonify(filters=filters, answer=answer)


def _text_endpoint(fn):
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text:
        return jsonify(error="Please paste some text first."), 400
    if len(text) > 15000:
        return jsonify(error="That's too long. Please paste up to about 15,000 characters."), 400
    text, _ = redact(text)  # never send SSNs or account numbers to the model
    try:
        return jsonify(answer=fn(text))
    except Exception:
        return jsonify(error="Something went wrong. Please try again."), 500


@app.post("/api/extract")
def extract():
    """Read an uploaded document and return its text with SSNs and account numbers removed."""
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify(error="Please choose a file."), 400
    try:
        text, used_ocr = extract_text(upload.filename, upload.read())
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception:
        return jsonify(error="We couldn't read that file. Try a different copy, or paste the text."), 400
    if not text:
        return jsonify(error="No text found. Try a clearer photo, or paste the text instead."), 400
    text, counts = redact(text, ocr=used_ocr)
    return jsonify(text=text, redactions=counts, ocr=used_ocr)


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="That file is too big. Please upload one under 10 MB."), 413


@app.post("/api/lease")
def lease():
    return _text_endpoint(explain_lease)


@app.post("/api/listing")
def listing():
    return _text_endpoint(check_listing)


if __name__ == "__main__":
    app.run(port=8000, debug=True)
