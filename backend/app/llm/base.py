from __future__ import annotations
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    model: str = "unknown"

    @abstractmethod
    async def generate_json(
        self,
        system_prompt: str,
        user_payload: dict,
        schema: dict,
    ) -> dict:
        ...
