import json
import urllib.request
import config
from .base import BaseLLMProvider

class CerebrasLLMProvider(BaseLLMProvider):
    """Cerebras Cloud API Provider adapter (Ultra-fast Llama 3.3 70B)."""

    def __init__(self, api_key: str = None, model_name: str = getattr(config, "CEREBRAS_MODEL", "llama3.3-70b")):
        self.api_key = api_key or getattr(config, "CEREBRAS_API_KEY", "")
        self.model_name = model_name

        if not self.api_key:
            print("[Warning] CEREBRAS_API_KEY not set. Cerebras generations will require an API key.")

    @property
    def provider_name(self) -> str:
        return "Cerebras Cloud API (Llama 3.3)"

    def generate_answer(self, system_prompt: str, user_prompt: str, api_key: str = None, images: list = None, **kwargs) -> str:
        active_key_raw = api_key or self.api_key
        if not active_key_raw:
            return "[Error: CEREBRAS_API_KEY missing. Please set your key in .env or Vercel.]"

        # Support comma-separated API keys for rotation/failover
        keys = [k.strip() for k in active_key_raw.split(",") if k.strip()]
        last_error = None

        url = "https://api.cerebras.ai/v1/chat/completions"

        candidates = ["llama-3.3-70b", "llama3.1-8b", "llama-3.1-70b", "gpt-oss-120b", "gemma-4-31b", "zai-glm-4.7", self.model_name]
        
        for active_key in keys:
            for model_candidate in candidates:
                try:
                    payload = {
                        "model": model_candidate,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2,
                        "max_completion_tokens": 1024
                    }
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {active_key}",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        },
                        method="POST"
                    )

                    with urllib.request.urlopen(req, timeout=30) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        if "choices" in resp_data and len(resp_data["choices"]) > 0:
                            return resp_data["choices"][0]["message"]["content"]
                except Exception as e:
                    last_error = str(e)
                    print(f"[Cerebras Warning] Model {model_candidate} with Key ...{active_key[-6:]} failed: {e}")
                    if "402" in last_error:
                        return (
                            "⚠️ **Cerebras API Verification Required (HTTP 402)**\n\n"
                            "Cerebras authenticated your API key successfully, but returned a payment/verification check.\n\n"
                            "**Fix**: Log into [cloud.cerebras.ai](https://cloud.cerebras.ai/), go to **Limits** or **Billing**, and activate free tier usage."
                        )
                    continue

        return f"[Cerebras Error: {last_error or 'Could not generate response with available Cerebras models.'}]"
