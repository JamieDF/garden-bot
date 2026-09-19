"""
Minimal OpenAI-compatible chat client.

Works with llama.cpp llama-server, Ollama, and hosted OpenAI-compatible
APIs - swap providers by changing GROW_LLM_BASE_URL / GROW_LLM_MODEL.
"""

import json
import logging
from typing import Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.api_key = api_key or settings.llm_api_key
        # Structured-output mode that works for this provider, detected lazily:
        # "json_schema" (enforced), "json_object" (prompted), or "none".
        self._rf_mode: Optional[str] = None

    async def chat(
        self,
        messages: list[dict],
        json_schema: Optional[dict] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat completion request, return the message content.

        If json_schema is provided, requests structured output. Falls back
        through json_schema -> json_object -> plain text depending on what
        the provider supports.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_schema is not None:
            return await self._chat_structured(payload, messages, json_schema)
        return await self._post(payload)

    async def _chat_structured(
        self, payload: dict, messages: list[dict], json_schema: dict
    ) -> str:
        modes = (
            [self._rf_mode]
            if self._rf_mode
            else ["json_schema", "json_object", "none"]
        )
        last_err: Optional[Exception] = None
        for mode in modes:
            p = dict(payload)
            if mode == "json_schema":
                p["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "response", "schema": json_schema},
                }
            else:
                hint = (
                    "\nRespond with JSON only, matching this schema: "
                    + json.dumps(json_schema)
                )
                p["messages"] = self._with_hint(messages, hint)
                if mode == "json_object":
                    p["response_format"] = {"type": "json_object"}
            try:
                content = await self._post(p)
                if self._rf_mode is None:
                    self._rf_mode = mode
                    logger.info(f"LLM structured output mode: {mode}")
                return content
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    last_err = e
                    continue
                raise
        raise last_err  # type: ignore[misc]

    @staticmethod
    def _with_hint(messages: list[dict], hint: str) -> list[dict]:
        """Append a schema hint to the system message (or prepend one)."""
        msgs = [dict(m) for m in messages]
        if msgs and msgs[0].get("role") == "system":
            msgs[0]["content"] += hint
        else:
            msgs.insert(0, {"role": "system", "content": hint})
        return msgs

    async def _post(self, payload: dict) -> str:
        headers = {}
        if self.api_key and self.api_key != "none":
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
