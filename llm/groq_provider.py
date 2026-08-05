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

    def generate_answer(self, system_prompt: str, user_prompt: str, api_key: str = None) -> str:
        active_key = api_key or self.api_key
        if not active_key:
            return "[Error: GROQ_API_KEY missing. Please set your key in the Web UI sidebar or .env file.]"

        try:
            from groq import Groq
            client = Groq(api_key=active_key)
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1024
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"[Groq Error: {str(e)}]"
