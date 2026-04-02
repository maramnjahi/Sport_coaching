from __future__ import annotations

from typing import Any

from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.config import ALLOWED_COLLECTIONS, Settings
from app.db.qdrant_client import get_qdrant


class VectorService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def ensure_collections(self) -> None:
        client = get_qdrant()
        existing = {collection.name for collection in (await client.get_collections()).collections}
        for name in sorted(ALLOWED_COLLECTIONS):
            if name in existing:
                continue
            await client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=self._settings.qdrant_vector_size,
                    distance=Distance.COSINE,
                ),
            )

    async def upsert_chunks(
        self,
        *,
        collection: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        if not vectors or len(vectors) != len(payloads) or len(vectors) != len(ids):
            raise ValueError("vectors, payloads, and ids must have the same non-zero length")
        client = get_qdrant()
        points: list[PointStruct] = []
        for index, vector in enumerate(vectors):
            points.append(
                PointStruct(
                    id=ids[index],
                    vector=vector,
                    payload=payloads[index],
                )
            )
        await client.upsert(collection_name=collection, points=points)

    async def search(
        self,
        *,
        collection: str,
        vector: list[float],
        limit: int,
    ) -> list[dict[str, Any]]:
        client = get_qdrant()
        response = await client.query_points(
            collection_name=collection,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        hits: list[dict[str, Any]] = []
        for point in response.points:
            score = point.score if point.score is not None else 0.0
            payload = dict(point.payload or {})
            hits.append(
                {
                    "id": str(point.id),
                    "score": float(score),
                    "payload": payload,
                }
            )
        return hits
