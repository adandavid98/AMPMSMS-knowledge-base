import requests
import config
from .base import BaseLLMProvider

class OllamaLLMProvider(BaseLLMProvider):
    """Local Ollama Provider adapter."""

    def __init__(self, host: str = None, model_name: str = config.OLLAMA_MODEL):
        self.host = host or config.OLLAMA_HOST
        self.model_name = model_name

    @property
    def provider_name(self) -> str:
        return f"Local Ollama ({self.model_name})"

    def generate_answer(self, system_prompt: str, user_prompt: str, api_key: str = None, images: list = None, **kwargs) -> str:
        url = f"{self.host.rstrip('/')}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.2}
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            else:
                return f"[Ollama HTTP Error {response.status_code}: {response.text}]"
        except requests.exceptions.ConnectionError:
            return f"[Ollama Error: Could not connect to Ollama host at {self.host}. Ensure Ollama service is running.]"
        except Exception as e:
            return f"[Ollama Error: {str(e)}]"
