from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    query: str = Field(min_length=1)
    sport: str = Field(min_length=1)
    session_id: Optional[str] = Field(default=None, alias="session_id")


class SourceAttribution(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    document_id: Optional[str] = Field(default=None, serialization_alias="documentId")
    page: Optional[int] = None
    text: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    response: str
    sources: list[dict[str, Any]]
    latency_ms: int = Field(serialization_alias="latencyMs")
