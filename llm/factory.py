import config
from .base import BaseLLMProvider
from .gemini_provider import GeminiLLMProvider
from .groq_provider import GroqLLMProvider
from .ollama_provider import OllamaLLMProvider

def get_llm_provider(name: str = None) -> BaseLLMProvider:
    """
    Factory function returning the specified LLM provider instance.
    Defaults to config.DEFAULT_LLM_PROVIDER ('gemini').
    """
    provider_name = (name or config.DEFAULT_LLM_PROVIDER).lower().strip()

    if provider_name == "gemini":
        return GeminiLLMProvider()
    elif provider_name == "groq":
        return GroqLLMProvider()
    elif provider_name == "ollama":
        return OllamaLLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider '{provider_name}'. Supported options: gemini, groq, ollama")
