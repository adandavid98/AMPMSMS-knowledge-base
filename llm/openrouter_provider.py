import json
import re
import urllib.request
import config
from .base import BaseLLMProvider

def _clean_openrouter_content(content: str) -> str:
    """Strips raw thinking traces and tool markers from free model outputs."""
    if not content:
        return ""
    # Strip <think>...</think> or <thought>...</thought> tags
    content = re.sub(r'(?s)<(think|thought)>.*?</\1>', '', content)
    # Strip "Here's a thinking process: ... \n\n" if followed by answer
    content = re.sub(r"(?s)^Here's a thinking process:.*?\n\n", '', content)
    # Strip tool call artifacts
    content = re.sub(r'(?s)<\|tool_call_start\|>.*?<\|tool_call_end\|>', '', content)
    return content.strip()

class OpenRouterLLMProvider(BaseLLMProvider):
    """OpenRouter API Provider adapter with automatic verified free models fallback."""

    def __init__(self, api_key: str = None, model_name: str = getattr(config, "OPENROUTER_MODEL", "dots-studio/dots-3-note-preview:free")):
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

        # Verified active operational free open-source models on OpenRouter
        candidates = [
            self.model_name,
            "dots-studio/dots-3-note-preview:free",
            "minimax/minimax-m2.7:free",
            "cohere/north-mini-code:free",
            "nvidia/nemotron-3.5-lightning:free",
            "google/gemma-4-31b-it:free",
            "google/gemma-4-26b-a4b-it:free",
            "liquid/lfm-2.5-2.6b:free",
            "z-ai/glm-5.2:free"
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
                            content = resp_data["choices"][0]["message"].get("content", "")
                            # Verify response is not an empty string or upstream JSON error
                            if content and not content.startswith('{"message":"Upstream error') and not content.startswith('{"error":'):
                                cleaned = _clean_openrouter_content(content)
                                if cleaned:
                                    return cleaned
                except Exception as e:
                    last_error = str(e)
                    print(f"[OpenRouter Warning] Model {model_candidate} with Key ...{active_key[-6:]} failed: {e}")
                    continue

        return f"[OpenRouter Error: {last_error or 'Could not generate response with available OpenRouter models.'}]"
