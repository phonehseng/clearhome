"""Quick check that your API key works and the model responds.

Usage: python backend/test_gemma.py [model-name]
"""
import os
import sys

from dotenv import load_dotenv
from google import genai

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key.startswith("AIza...") or api_key == "your-key-here":
    raise SystemExit("Set GEMINI_API_KEY in the .env file at the project root.")

model = sys.argv[1] if len(sys.argv) > 1 else "gemma-4-26b-a4b-it"
client = genai.Client(api_key=api_key)

if "--list" in sys.argv:
    for m in client.models.list():
        if "gemma" in m.name.lower():
            print(m.name)
    raise SystemExit

print(f"Using model: {model}")
try:
    response = client.models.generate_content(
        model=model,
        contents="In one sentence, what is affordable housing?",
    )
except Exception as e:
    raise SystemExit(f"Request failed: {type(e).__name__}: {e}")
print(response.text)
