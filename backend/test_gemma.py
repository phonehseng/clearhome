"""Quick check that your API key works and Gemma 4 responds."""
import os

from dotenv import load_dotenv
from google import genai

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key.startswith("AIza...") or api_key == "your-key-here":
    raise SystemExit("Set GEMINI_API_KEY in the .env file at the project root.")

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents="In one sentence, what is affordable housing?",
)
print(response.text)
