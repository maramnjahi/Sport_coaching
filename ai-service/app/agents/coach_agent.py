from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    build_embed_query_node,
    build_generate_node,
    build_graph_enrich_node,
    build_retrieve_node,
)
from app.agents.state import AgentState
from app.config import Settings
from app.services.embedding_service import EmbeddingService
from app.services.graph_service import GraphService
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService

_compiled_graph: Any | None = None


def build_coach_graph(
    *,
    settings: Settings,
    embedding: EmbeddingService,
    vector: VectorService,
    graph: GraphService,
    llm: LLMService,
) -> Any:
    del settings
    global _compiled_graph
    workflow = StateGraph(AgentState)
    embed_query_node = build_embed_query_node(embedding)
    retrieve_node = build_retrieve_node(vector)
    graph_enrich_node = build_graph_enrich_node(graph)
    generate_node = build_generate_node(llm)
    workflow.add_node("embed_query_node", embed_query_node)
    workflow.add_node("retrieve_node", retrieve_node)
    workflow.add_node("graph_enrich_node", graph_enrich_node)
    workflow.add_node("generate_node", generate_node)
    workflow.add_edge(START, "embed_query_node")
    workflow.add_edge("embed_query_node", "retrieve_node")
    workflow.add_conditional_edges(
        "retrieve_node",
        lambda state: "end" if state.get("error") else "continue",
        {"end": END, "continue": "graph_enrich_node"},
    )
    workflow.add_edge("graph_enrich_node", "generate_node")
    workflow.add_edge("generate_node", END)
    _compiled_graph = workflow.compile()
    return _compiled_graph


async def run_agent(query: str, sport: str) -> dict[str, Any]:
    if _compiled_graph is None:
        raise RuntimeError("agent graph is not initialized")
    initial_state: AgentState = {"query": query, "sport": sport}
    state = await _compiled_graph.ainvoke(initial_state)
    error = state.get("error")
    if error:
        return {"response": str(error), "sources": []}
    answer = str(state.get("final_answer") or "")
    chunks = list(state.get("retrieved_chunks") or [])
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for chunk in chunks:
        key = f"{chunk.get('document_id','')}|{chunk.get('page','')}|{chunk.get('source','')}"
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "documentId": str(chunk.get("document_id") or "") or None,
                "page": int(chunk.get("page") or 0) or None,
                "score": float(chunk.get("score") or 0.0),
                "text": str(chunk.get("text") or "")[:500] or None,
                "source": str(chunk.get("source") or ""),
            }
        )
    return {"response": answer, "sources": sources}
