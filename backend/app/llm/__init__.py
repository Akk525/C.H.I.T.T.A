from __future__ import annotations
import os

from .base import LLMProvider


def get_provider() -> LLMProvider:
    name = os.environ.get("CHITTA_LLM_PROVIDER", "mock").strip().lower()
    if name == "claude":
        from .claude_provider import ClaudeProvider

        return ClaudeProvider()
    if name == "gemini":
        from .gemini_provider import GeminiProvider

        return GeminiProvider()
    if name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()
    from .mock_provider import MockProvider

    return MockProvider()
