import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY")

print("Fetching OpenRouter free models...")
try:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "Mozilla/5.0"
        }
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        models = data.get("data", [])
        free_models = [m["id"] for m in models if ":free" in m["id"] or "free" in m.get("pricing", {}).get("prompt", "1")]
        print(f"Found {len(free_models)} free models:")
        for fm in free_models[:15]:
            print(" -", fm)
except Exception as e:
    print("Error:", e)
