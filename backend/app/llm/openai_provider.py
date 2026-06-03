from __future__ import annotations
import json
import os

from openai import AsyncOpenAI

from .base import LLMProvider
from .json_utils import parse_json_object


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        self.model = os.environ.get("CHITTA_SYNTHESIS_MODEL", "gpt-4.1-mini")
        self.client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    async def generate_json(
        self,
        system_prompt: str,
        user_payload: dict,
        schema: dict,
    ) -> dict:
        response = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=8192,
        )
        raw = response.choices[0].message.content or "{}"
        return parse_json_object(raw)
