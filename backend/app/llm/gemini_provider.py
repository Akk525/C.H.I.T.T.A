from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

from .base import LLMProvider
from .json_utils import parse_json_object

_COMPACT_RETRY_HINT = (
    "Your previous reply was invalid JSON. Return ONE compact JSON object only. "
    "Keep each narrative field to 1-2 sentences and at most 3 citations."
)


def _to_gemini_schema(node: Any) -> Any:
    """Convert JSON Schema types to Gemini's uppercase schema convention."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key == "type" and isinstance(value, str):
                out[key] = value.upper()
            else:
                out[key] = _to_gemini_schema(value)
        return out
    if isinstance(node, list):
        return [_to_gemini_schema(item) for item in node]
    return node


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = os.environ.get("GOOGLE_API_KEY", "").strip() or os.environ.get(
            "GEMINI_API_KEY", ""
        ).strip()
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY (or GEMINI_API_KEY) is required when "
                "CHITTA_LLM_PROVIDER=gemini"
            )
        self.model = os.environ.get("CHITTA_SYNTHESIS_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=api_key)

    def _config(self, system_prompt: str, schema: dict, *, compact: bool) -> types.GenerateContentConfig:
        instruction = system_prompt
        if compact:
            instruction = f"{system_prompt}\n\n{_COMPACT_RETRY_HINT}"
        return types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=0.2,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=_to_gemini_schema(schema),
        )

    def _parse_response(self, response: types.GenerateContentResponse) -> dict:
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, dict):
            return parsed
        if parsed is not None and hasattr(parsed, "model_dump"):
            dumped = parsed.model_dump()
            if isinstance(dumped, dict):
                return dumped

        raw = (response.text or "").strip()
        if not raw:
            raise ValueError("Gemini returned an empty response")
        return parse_json_object(raw)

    async def generate_json(
        self,
        system_prompt: str,
        user_payload: dict,
        schema: dict,
    ) -> dict:
        user_json = json.dumps(user_payload, ensure_ascii=False)
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    text=(
                                        "Produce the synthesis JSON for this evidence payload.\n\n"
                                        f"{user_json}"
                                    )
                                )
                            ],
                        )
                    ],
                    config=self._config(system_prompt, schema, compact=attempt > 0),
                )
                return self._parse_response(response)
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                last_error = exc
            except Exception as exc:
                # Non-JSON failures (API errors) should not silently retry.
                if attempt == 0 and "json" in str(exc).lower():
                    last_error = exc
                    continue
                raise

        assert last_error is not None
        raise last_error
