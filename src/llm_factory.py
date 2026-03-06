from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from .config import Config


def create_llm():
    """Factory function to create LLM instance based on provider configuration.

    Returns:
        Configured LLM instance (ChatGoogleGenerativeAI or ChatOllama).

    Raises:
        ValueError: If provider is not supported.
    """
    provider = Config.LLM_PROVIDER.lower()

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=Config.LLM_MODEL,
            api_key=Config.GEMINI_API_KEY,
            temperature=Config.LLM_TEMPERATURE,
        )
    elif provider == "ollama":
        return ChatOllama(
            model=Config.LLM_MODEL,
            base_url=Config.OLLAMA_BASE_URL,
            temperature=Config.LLM_TEMPERATURE,
        )
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. Supported providers: gemini, ollama"
        )
