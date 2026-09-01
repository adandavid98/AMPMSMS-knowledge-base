import os
import json
import urllib.request
import config
from .base import BaseLLMProvider

class CerebrasLLMProvider(BaseLLMProvider):
    """Cerebras Cloud API Provider adapter (Ultra-fast Llama 3.3 70B)."""

    def __init__(self, api_key: str = None, model_name: str = getattr(config, "CEREBRAS_MODEL", "gpt-oss-120b")):
        self.api_key = api_key or getattr(config, "CEREBRAS_API_KEY", "") or os.getenv("CerebrasAMPM_API_KEY", "") or os.getenv("CEREBRAS_API_KEY", "")
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
            "gpt-oss-120b",
            "gemma-4-31b",
            "llama-3.3-70b",
            "llama3.3-70b",
            "llama-3.1-8b"
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
                except urllib.error.HTTPError as he:
                    error_body = he.read().decode("utf-8", errors="ignore")
                    if he.code == 402 or "payment_required" in error_body:
                        return (
                            "⚠️ **Cerebras API - Activación de Plan Requerida (HTTP 402)**\n\n"
                            "Tu API Key de Cerebras es válida, pero tu cuenta requiere activar el nivel de facturación/límites en la consola de Cerebras.\n\n"
                            "**Solución**:\n"
                            "1. Inicia sesión en **[cloud.cerebras.ai](https://cloud.cerebras.ai/)**.\n"
                            "2. Ve a la pestaña **Billing / Limits** y activa el acceso a la API."
                        )
                    if he.code == 401 or "unauthorized" in error_body:
                        return "[Cerebras Error: Invalid or expired CEREBRAS_API_KEY. Please verify your Cerebras API key in the settings panel.]"
                    if he.code == 429:
                        return "[Cerebras Error: Rate limit reached on Cerebras. Please wait 1 minute or switch to Google Gemini.]"
                    last_error = f"HTTP {he.code}: {error_body}"
                    print(f"[Cerebras Warning] Model {model_candidate} failed with HTTP {he.code}: {error_body}")
                    continue
                except Exception as e:
                    last_error = str(e)
                    print(f"[Cerebras Warning] Model {model_candidate} with Key ...{active_key[-6:]} failed: {e}")
                    continue

        return f"[Cerebras Error: {last_error or 'Could not generate response with available Cerebras models.'}]"
