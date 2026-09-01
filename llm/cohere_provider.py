import os
import json
import urllib.request
import urllib.error
import config
from .base import BaseLLMProvider

class CohereLLMProvider(BaseLLMProvider):
    """Cohere API Provider adapter (Command R / Command R+ RAG Specialist)."""

    def __init__(self, api_key: str = None, model_name: str = getattr(config, "COHERE_MODEL", "command-r-08-2024")):
        self.api_key = api_key or getattr(config, "COHERE_API_KEY", "") or os.getenv("CohereAMPM_API_KEY", "") or os.getenv("COHERE_API_KEY", "")
        self.model_name = model_name

        if not self.api_key:
            print("[Warning] COHERE_API_KEY not set. Cohere generations will require an API key.")

    @property
    def provider_name(self) -> str:
        return "Cohere API (Command R)"

    def generate_answer(self, system_prompt: str, user_prompt: str, api_key: str = None, images: list = None, **kwargs) -> str:
        active_key_raw = api_key or self.api_key
        if not active_key_raw:
            return "[Error: COHERE_API_KEY missing. Please set your key in .env or the Web UI sidebar.]"

        # Support comma-separated API keys for rotation/failover
        keys = [k.strip() for k in active_key_raw.split(",") if k.strip()]
        last_error = None

        url_v2 = "https://api.cohere.com/v2/chat"
        url_v1 = "https://api.cohere.com/v1/chat"

        # Active verified Cohere models
        candidates = [
            self.model_name,
            "command-r-08-2024",
            "command-r-plus-08-2024",
            "command-r",
            "command-r-plus",
            "command"
        ]
        unique_candidates = []
        for c in candidates:
            if c and c not in unique_candidates:
                unique_candidates.append(c)

        for active_key in keys:
            for model_candidate in unique_candidates:
                # Try v2 Chat API first
                try:
                    payload = {
                        "model": model_candidate,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2
                    }
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        url_v2,
                        data=data,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {active_key}",
                            "User-Agent": "AMPM-POS-Assistant/1.0"
                        },
                        method="POST"
                    )

                    with urllib.request.urlopen(req, timeout=35) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        if "message" in resp_data and "content" in resp_data["message"]:
                            content_blocks = resp_data["message"]["content"]
                            if isinstance(content_blocks, list) and len(content_blocks) > 0:
                                text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
                                if text.strip():
                                    return text.strip()
                except urllib.error.HTTPError as he:
                    error_body = he.read().decode("utf-8", errors="ignore")
                    if he.code == 401 or "unauthorized" in error_body.lower() or "invalid_api_key" in error_body.lower():
                        return "[Cohere Error: Invalid or expired COHERE_API_KEY. Please verify your Cohere key in the settings panel.]"
                    if he.code == 429:
                        return "[Cohere Error: Rate limit (RPM) reached on Cohere free tier. Please wait a moment or switch to Google Gemini.]"
                    last_error = f"HTTP {he.code}: {error_body}"
                    print(f"[Cohere Warning v2] Model {model_candidate} failed with HTTP {he.code}: {error_body}")
                except Exception as e:
                    last_error = str(e)
                    print(f"[Cohere Warning v2] Model {model_candidate} failed: {e}")

                # Fallback to v1 Chat API if v2 fails
                try:
                    payload_v1 = {
                        "model": model_candidate,
                        "preamble": system_prompt,
                        "message": user_prompt,
                        "temperature": 0.2
                    }
                    data_v1 = json.dumps(payload_v1).encode("utf-8")
                    req_v1 = urllib.request.Request(
                        url_v1,
                        data=data_v1,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {active_key}",
                            "User-Agent": "AMPM-POS-Assistant/1.0"
                        },
                        method="POST"
                    )

                    with urllib.request.urlopen(req_v1, timeout=35) as resp_v1:
                        resp_data_v1 = json.loads(resp_v1.read().decode("utf-8"))
                        if "text" in resp_data_v1 and resp_data_v1["text"]:
                            return resp_data_v1["text"].strip()
                except urllib.error.HTTPError as he_v1:
                    error_body_v1 = he_v1.read().decode("utf-8", errors="ignore")
                    if he_v1.code == 401:
                        return "[Cohere Error: Invalid or expired COHERE_API_KEY. Please verify your Cohere key in the settings panel.]"
                    last_error = f"HTTP {he_v1.code}: {error_body_v1}"
                except Exception as e:
                    last_error = str(e)

        return f"[Cohere Error: {last_error or 'Could not generate response with available Cohere models.'}]"
