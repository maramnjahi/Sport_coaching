from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _bootstrap_path() -> None:
    os.chdir(ROOT)
    path_root = str(ROOT)
    if path_root not in sys.path:
        sys.path.insert(0, path_root)


async def _run() -> None:
    import httpx

    from app.config import get_settings
    from app.db.neo4j_client import init_neo4j, neo4j_driver_ready, shutdown_neo4j
    from app.db.qdrant_client import init_qdrant, shutdown_qdrant
    from app.services.embedding_service import EmbeddingService
    from app.services.graph_service import GraphService
    from app.services.ingest_service import IngestService
    from app.services.llm_service import LLMService
    from app.services.vector_service import VectorService

    get_settings.cache_clear()
    settings = get_settings()
    base_url = settings.nvidia_base_url.rstrip("/") + "/"
    init_qdrant(settings.qdrant_path)
    if settings.neo4j_enabled:
        await init_neo4j(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
    async with httpx.AsyncClient(
        base_url=base_url,
        headers=settings.nim_headers(),
        timeout=settings.http_timeout_override_seconds,
    ) as nim_http:
        embedding = EmbeddingService(settings, nim_http)
        llm = LLMService(settings, nim_http)
        vector = VectorService(settings)
        graph = GraphService(settings)
        ingest = IngestService(settings, embedding, vector, graph, llm)
        await vector.ensure_collections()
        await graph.ensure_domain_nodes()
        totals = await ingest.ingest_all_collections()
    await shutdown_qdrant()
    if neo4j_driver_ready():
        await shutdown_neo4j()
    for sport, count in sorted(totals.items()):
        print(f"{sport}: {count} chunks indexed")


def main() -> None:
    _bootstrap_path()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
