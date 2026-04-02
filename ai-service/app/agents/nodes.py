from __future__ import annotations

from typing import Any

from app.agents.state import AgentState
from app.db.neo4j_client import neo4j_driver_ready
from app.services.embedding_service import EmbeddingService
from app.services.graph_service import GraphService
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService

_SYSTEM_PROMPT = (
    "You are an expert sports coach assistant. Answer only based on the provided context. "
    "If the context does not contain enough information, say so honestly. Do not invent information."
)


def build_embed_query_node(embedding_service: EmbeddingService):
    async def embed_query_node(state: AgentState) -> dict[str, Any]:
        try:
            vector = await embedding_service.embed_query(state["query"])
            return {"embedded_query": vector, "error": None}
        except Exception as exc:
            return {"error": f"embedding failed: {exc}"}

    return embed_query_node


def build_retrieve_node(vector_service: VectorService):
    async def retrieve_node(state: AgentState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        try:
            hits = await vector_service.search(
                collection=state["sport"],
                vector=list(state["embedded_query"]),
                limit=5,
            )
            chunks: list[dict[str, object]] = []
            for hit in hits:
                payload = dict(hit.get("payload") or {})
                chunks.append(
                    {
                        "text": str(payload.get("text") or ""),
                        "score": float(hit.get("score") or 0.0),
                        "source": str(payload.get("source") or ""),
                        "document_id": str(payload.get("document_id") or ""),
                        "page": int(payload.get("page") or 0),
                        "chunk_id": str(hit.get("id") or ""),
                    }
                )
            if not chunks:
                return {"retrieved_chunks": [], "error": "no relevant content found"}
            return {"retrieved_chunks": chunks, "error": None}
        except Exception as exc:
            return {"error": f"retrieval failed: {exc}"}

    return retrieve_node


def build_graph_enrich_node(graph_service: GraphService):
    async def graph_enrich_node(state: AgentState) -> dict[str, Any]:
        if not neo4j_driver_ready():
            return {"graph_context": ""}
        try:
            graph_context = await graph_service.query_related_entities(
                query=state["query"],
                domain=state["sport"],
            )
            return {"graph_context": graph_context}
        except Exception:
            return {"graph_context": ""}

    return graph_enrich_node


def build_generate_node(llm_service: LLMService):
    async def generate_node(state: AgentState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        try:
            chunks = list(state.get("retrieved_chunks") or [])
            context_blocks: list[str] = []
            for chunk in chunks:
                context_blocks.append(
                    f"[Source: {chunk.get('source', '')} | Score: {float(chunk.get('score', 0.0)):.2f}]\n"
                    f"{chunk.get('text', '')}"
                )
            user_parts = ["\n\n".join(context_blocks)]
            graph_context = str(state.get("graph_context") or "").strip()
            if graph_context:
                user_parts.append(f"[Knowledge Graph Context]\n{graph_context}")
            user_parts.append(f"User question: {state['query']}")
            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ]
            response = await llm_service.chat(messages=messages)
            return {"final_answer": response, "error": None}
        except Exception as exc:
            return {"error": f"generation failed: {exc}"}

    return generate_node
