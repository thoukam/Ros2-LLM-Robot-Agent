from __future__ import annotations

from robot_agent.llm.base import BaseLLMProvider


def create_llm_provider(provider: str, model: str, ollama_host: str) -> BaseLLMProvider:
    provider = provider.lower()

    if provider == "openai":
        from robot_agent.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(model=model)

    if provider == "claude":
        from robot_agent.llm.claude_provider import ClaudeProvider
        return ClaudeProvider(model=model)

    if provider == "mistral":
        from robot_agent.llm.mistral_provider import MistralProvider
        return MistralProvider(model=model)

    if provider == "ollama":
        from robot_agent.llm.ollama_provider import OllamaProvider
        return OllamaProvider(model=model, host=ollama_host)

    raise ValueError(f"Unsupported provider: {provider}")