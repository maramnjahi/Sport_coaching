from __future__ import annotations

from typing import Optional

from qdrant_client import AsyncQdrantClient

_client: Optional[AsyncQdrantClient] = None


def init_qdrant(path: str) -> None:
    global _client
    _client = AsyncQdrantClient(path=path)


async def shutdown_qdrant() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def get_qdrant() -> AsyncQdrantClient:
    if _client is None:
        raise RuntimeError("AsyncQdrantClient is not initialized")
    return _client
