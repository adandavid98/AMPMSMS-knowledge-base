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

        # Fallback list of active Groq models in case one is unavailable or deprecated
        candidates = [
            self.model_name,
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "gemma2-9b-it",
            "qwen3.8-27b",
            "llama3-70b-8192",
            "llama3-8b-8192"
        ]
        unique_candidates = []
        for c in candidates:
            if c and c not in unique_candidates:
                unique_candidates.append(c)

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
                    last_error = str(e)
                    print(f"[Groq Warning] Model {model_candidate} with Key ...{active_key[-6:]} failed: {e}")
                    continue

        return f"[Groq Error: {last_error or 'Could not generate response with available Groq keys.'}]"
