from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM Providers (Gemini, Groq, Ollama)."""

    @abstractmethod
    def generate_answer(self, system_prompt: str, user_prompt: str, api_key: str = None, images: list = None) -> str:
        """Generates a text completion response given system and user prompts, optionally using custom API key and images."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the provider name."""
        pass
