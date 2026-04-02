from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.agents.coach_agent import build_coach_graph
from app.api.v1.router import api_router
from app.config import get_settings
from app.db.mongo_client import init_mongo, shutdown_mongo
from app.db.neo4j_client import init_neo4j, neo4j_driver_ready, shutdown_neo4j
from app.db.qdrant_client import init_qdrant, shutdown_qdrant
from app.services.embedding_service import EmbeddingService
from app.services.graph_service import GraphService
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    base_url = settings.nvidia_base_url.rstrip("/") + "/"
    async with httpx.AsyncClient(
        base_url=base_url,
        headers=settings.nim_headers(),
        timeout=settings.http_timeout_override_seconds,
    ) as nim_http:
        init_qdrant(settings.qdrant_path)
        init_mongo(settings.mongo_uri, settings.mongo_db)
        if settings.neo4j_enabled:
            await init_neo4j(
                settings.neo4j_uri,
                settings.neo4j_user,
                settings.neo4j_password,
            )
        embedding_service = EmbeddingService(settings, nim_http)
        llm_service = LLMService(settings, nim_http)
        vector_service = VectorService(settings)
        graph_service = GraphService(settings)
        await vector_service.ensure_collections()
        await graph_service.ensure_domain_nodes()
        coach_graph = build_coach_graph(
            settings=settings,
            embedding=embedding_service,
            vector=vector_service,
            graph=graph_service,
            llm=llm_service,
        )
        app.state.settings = settings
        app.state.embedding_service = embedding_service
        app.state.llm_service = llm_service
        app.state.vector_service = vector_service
        app.state.graph_service = graph_service
        app.state.coach_graph = coach_graph
        yield
    await shutdown_qdrant()
    await shutdown_mongo()
    if neo4j_driver_ready():
        await shutdown_neo4j()


def create_app() -> FastAPI:
    application = FastAPI(title="CoachMind AI", lifespan=lifespan)
    application.include_router(api_router)

    @application.get("/health")
    async def health() -> dict[str, str | bool]:
        settings = get_settings()
        return {
            "status": "ok",
            "neo4j_enabled": settings.neo4j_enabled,
            "neo4j_connected": neo4j_driver_ready(),
        }

    return application


app = create_app()
