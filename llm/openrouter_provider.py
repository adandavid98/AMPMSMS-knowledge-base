import json
import urllib.request
import config
from .base import BaseLLMProvider

class OpenRouterLLMProvider(BaseLLMProvider):
    """OpenRouter API Provider adapter (Free Llama 3.3, Gemma 2, Mistral, Qwen)."""

    def __init__(self, api_key: str = None, model_name: str = getattr(config, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")):
        self.api_key = api_key or getattr(config, "OPENROUTER_API_KEY", "")
        self.model_name = model_name

        if not self.api_key:
            print("[Warning] OPENROUTER_API_KEY not set. OpenRouter generations will require an API key.")

    @property
    def provider_name(self) -> str:
        return "OpenRouter API (Free Models)"

    def generate_answer(self, system_prompt: str, user_prompt: str, api_key: str = None, images: list = None, **kwargs) -> str:
        active_key_raw = api_key or self.api_key
        if not active_key_raw:
            return "[Error: OPENROUTER_API_KEY missing. Please set your key in .env or Vercel.]"

        # Support comma-separated API keys for rotation/failover
        keys = [k.strip() for k in active_key_raw.split(",") if k.strip()]
        last_error = None

        url = "https://openrouter.ai/api/v1/chat/completions"

        # Fallback list of active free open-source models on OpenRouter
        candidates = [
            self.model_name,
            "meta-llama/llama-3.3-70b-instruct:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "google/gemma-2-9b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen-2.5-72b-instruct:free"
        ]
        
        # Deduplicate while preserving order
        unique_candidates = []
        for c in candidates:
            if c and c not in unique_candidates:
                unique_candidates.append(c)

        for active_key in keys:
            for model_candidate in unique_candidates:
                try:
                    payload = {
                        "model": model_candidate,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 1024
                    }
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {active_key}",
                            "HTTP-Referer": "https://ampmservice.com",
                            "X-Title": "AMPM POS Troubleshooting Assistant",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        },
                        method="POST"
                    )

                    with urllib.request.urlopen(req, timeout=30) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        if "choices" in resp_data and len(resp_data["choices"]) > 0:
                            return resp_data["choices"][0]["message"]["content"]
                except Exception as e:
                    last_error = str(e)
                    print(f"[OpenRouter Warning] Model {model_candidate} with Key ...{active_key[-6:]} failed: {e}")
                    continue

        return f"[OpenRouter Error: {last_error or 'Could not generate response with available OpenRouter models.'}]"
