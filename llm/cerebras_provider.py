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

        # Active verified Cerebras models
        candidates = [
            self.model_name,
            "llama-3.3-70b",
            "llama3.3-70b",
            "llama-3.1-8b",
            "llama3.1-8b",
            "llama-3.1-70b",
            "deepseek-r1-distill-llama-70b",
            "qwen-2.5-72b"
        ]
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
                        "max_completion_tokens": 1024
                    }
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {active_key}",
                            "User-Agent": "AMPM-POS-Assistant/1.0"
                        },
                        method="POST"
                    )

                    with urllib.request.urlopen(req, timeout=30) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        if "choices" in resp_data and len(resp_data["choices"]) > 0:
                            content = resp_data["choices"][0]["message"].get("content", "")
                            if content:
                                return content.strip()
                except Exception as e:
                    last_error = str(e)
                    print(f"[Cerebras Warning] Model {model_candidate} with Key ...{active_key[-6:]} failed: {e}")
                    if "401" in last_error or "unauthorized" in last_error.lower():
                        return "[Cerebras Error: Invalid or expired CEREBRAS_API_KEY. Please verify your Cerebras API key in the settings panel.]"
                    if "402" in last_error:
                        return (
                            "⚠️ **Cerebras API Verification Required (HTTP 402)**\n\n"
                            "Cerebras authenticated your API key successfully, but returned a verification check.\n\n"
                            "**Fix**: Log into [cloud.cerebras.ai](https://cloud.cerebras.ai/), go to **Settings > Billing/Limits**, and confirm free tier usage."
                        )
                    if "429" in last_error:
                        return "[Cerebras Error: Free tier rate limit (RPM/TPM) reached on Cerebras. Please wait 1 minute or switch to Gemini.]"
                    continue

        return f"[Cerebras Error: {last_error or 'Could not generate response with available Cerebras models.'}]"
