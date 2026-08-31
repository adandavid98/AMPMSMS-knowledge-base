import config
from .base import BaseLLMProvider

class GroqLLMProvider(BaseLLMProvider):
    """Groq API Provider adapter."""

    def __init__(self, api_key: str = None, model_name: str = config.GROQ_MODEL):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model_name = model_name

        if not self.api_key:
            print("[Warning] GROQ_API_KEY not set. Groq generations will require an API key.")

    @property
    def provider_name(self) -> str:
        return "Groq API"

    def generate_answer(self, system_prompt: str, user_prompt: str, api_key: str = None, images: list = None, **kwargs) -> str:
        active_key_raw = api_key or self.api_key
        if not active_key_raw:
            return "[Error: GROQ_API_KEY missing. Please set your key in the Web UI sidebar or .env file.]"

        # Support comma-separated API keys for rotation/failover
        keys = [k.strip() for k in active_key_raw.split(",") if k.strip()]
        last_error = None

        from groq import Groq

        # Active operational Groq models
        candidates = [
            self.model_name,
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "qwen-2.5-32b",
            "gemma2-9b-it"
        ]
        unique_candidates = []
        for c in candidates:
            if c and c not in unique_candidates:
                unique_candidates.append(c)

        rate_limited = False
        auth_failed = False
        detailed_errors = []

        for active_key in keys:
            for model_candidate in unique_candidates:
                try:
                    client = Groq(api_key=active_key)
                    completion = client.chat.completions.create(
                        model=model_candidate,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2,
                        max_tokens=1024
                    )
                    if completion and completion.choices:
                        return completion.choices[0].message.content
                except Exception as e:
                    err_str = str(e)
                    detailed_errors.append(f"{model_candidate}: {err_str}")
                    if "401" in err_str or "invalid_api_key" in err_str.lower() or "unauthorized" in err_str.lower():
                        auth_failed = True
                    elif "429" in err_str or "rate_limit" in err_str.lower():
                        rate_limited = True
                    print(f"[Groq Warning] Model {model_candidate} with Key ...{active_key[-6:]} failed: {e}")
                    continue

        if auth_failed:
            return "[Groq Error: Invalid or expired GROQ_API_KEY. Please verify your Groq key in the settings panel.]"
        if rate_limited:
            return "[Groq Error: Free tier rate limit (TPM/RPM) exceeded on Groq. Please wait 1 minute before retrying or use Google Gemini / OpenRouter.]"

        primary_error = detailed_errors[0] if detailed_errors else "Could not generate response with available Groq keys."
        return f"[Groq Error: {primary_error}]"
