from __future__ import annotations

import json
import os

from anthropic import AsyncAnthropic

from .base import LLMProvider
from .json_utils import parse_json_object


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required when CHITTA_LLM_PROVIDER=claude"
            )
        self.model = os.environ.get(
            "CHITTA_SYNTHESIS_MODEL", "claude-sonnet-4-20250514"
        )
        self.client = AsyncAnthropic(api_key=api_key)

    async def generate_json(
        self,
        system_prompt: str,
        user_payload: dict,
        schema: dict,
    ) -> dict:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            temperature=0.2,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                }
            ],
        )
        text_blocks = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        raw = "\n".join(text_blocks).strip() or "{}"
        return parse_json_object(raw)
