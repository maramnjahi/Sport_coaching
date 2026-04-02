from __future__ import annotations

from typing import Any, Literal

import httpx

from app.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http

    async def embed_texts(
        self,
        texts: list[str],
        *,
        input_type: Literal["query", "passage"] = "passage",
    ) -> list[list[float]]:
        if not texts:
            return []
        # API rejects empty strings (minLength 1); keep 1:1 alignment with callers.
        normalized = [(t.strip() if t and str(t).strip() else " ") for t in texts]
        payload: dict[str, Any] = {
            "model": self._settings.nvidia_embedding_model,
            "input": normalized,
            "input_type": input_type,
            "encoding_format": "float",
            # Default upstream is NONE → 400 if tokenizer count exceeds model max (~512 tokens).
            "truncate": "END",
        }
        response = await self._http.post(
            "embeddings",
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text[:2000] if response.text else "(empty body)"
            raise httpx.HTTPStatusError(
                f"{exc!s}\nNVIDIA response: {detail}",
                request=exc.request,
                response=exc.response,
            ) from exc
        body = response.json()
        rows = list(body.get("data", []))
        rows.sort(key=lambda item: int(item.get("index", 0)))
        return [list(map(float, row["embedding"])) for row in rows]

    async def embed_text(
        self,
        text: str,
        *,
        input_type: Literal["query", "passage"] = "query",
    ) -> list[float]:
        vectors = await self.embed_texts([text], input_type=input_type)
        if not vectors:
            raise RuntimeError("embedding response was empty")
        return vectors[0]

    async def embed_query(self, query: str) -> list[float]:
        return await self.embed_text(query, input_type="query")
