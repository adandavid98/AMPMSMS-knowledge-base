import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("CEREBRAS_API_KEY")

print("Testing Cerebras /v1/models endpoint...")
try:
    req = urllib.request.Request(
        "https://api.cerebras.ai/v1/models",
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "Mozilla/5.0"
        }
    )
    for model in ['gemma-4-31b', 'gpt-oss-120b', 'zai-glm-4.7', 'llama3.1-8b', 'llama-3.3-70b']:
        print(f"\n--- Testing model {model} ---")
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello! Say hi."}],
                "max_tokens": 50
            }
            data = json.dumps(payload).encode("utf-8")
            req_chat = urllib.request.Request(
                "https://api.cerebras.ai/v1/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                method="POST"
            )
            with urllib.request.urlopen(req_chat) as resp:
                res_body = json.loads(resp.read().decode("utf-8"))
                print("SUCCESS!", res_body["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as err:
            print("HTTPError:", err.code, err.read().decode("utf-8"))
        except Exception as ex:
            print("Error:", ex)
except Exception as e:
    print("Models error:", e)
