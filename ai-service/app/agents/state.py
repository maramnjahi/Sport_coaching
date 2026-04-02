from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    query: str
    sport: str
    embedded_query: list[float]
    retrieved_chunks: list[dict[str, object]]
    graph_context: str
    final_answer: str
    error: str | None
