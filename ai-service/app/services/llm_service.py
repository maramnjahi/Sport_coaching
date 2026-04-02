from __future__ import annotations

from typing import Any, Sequence

import httpx

from app.config import Settings

Message = dict[str, str]


class LLMService:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http

    async def chat_completion(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._settings.nvidia_llm_model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = await self._http.post(
            "chat/completions",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content")
        return self._normalize_content(content)

    async def chat(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": self._settings.nvidia_llm_model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        response = await self._http.post("chat/completions", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text[:2000] if response.text else "(empty body)"
            raise httpx.HTTPStatusError(
                f"{exc!s}\nNVIDIA response: {detail}",
                request=exc.request,
                response=exc.response,
            ) from exc
        data = response.json()
        choices = list(data.get("choices") or [])
        if not choices:
            return ""
        content = choices[0].get("message", {}).get("content")
        return self._normalize_content(content)

    def _normalize_content(self, content: str | list[Any] | None) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content.strip()
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            elif hasattr(block, "text"):
                parts.append(str(getattr(block, "text", "") or ""))
        return "".join(parts).strip()
