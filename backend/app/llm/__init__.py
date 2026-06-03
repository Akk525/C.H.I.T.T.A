from __future__ import annotations
import os

from .base import LLMProvider


def get_provider() -> LLMProvider:
    name = os.environ.get("CHITTA_LLM_PROVIDER", "mock").strip().lower()
    if name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider()
    from .mock_provider import MockProvider
    return MockProvider()
