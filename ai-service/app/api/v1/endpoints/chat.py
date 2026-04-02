from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.agents.coach_agent import run_agent
from app.config import ALLOWED_COLLECTIONS
from app.db.mongo_client import get_mongo_database
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def post_chat(payload: ChatRequest, request: Request) -> JSONResponse:
    started = time.perf_counter()
    sport_norm = payload.sport.strip().lower()
    if sport_norm not in ALLOWED_COLLECTIONS:
        raise HTTPException(status_code=400, detail="sport must be one of allowed collections")
    result = await run_agent(query=payload.query, sport=sport_norm)
    response_text = str(result.get("response") or "")
    sources = list(result.get("sources") or [])
    database = get_mongo_database()
    await database["chat_sessions"].insert_one(
        {
            "query": payload.query,
            "sport": sport_norm,
            "answer": response_text,
            "sources": sources,
            "created_at": datetime.now(timezone.utc),
        }
    )
    body = ChatResponse(
        response=response_text,
        sources=sources,
        latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
    ).model_dump(mode="json", by_alias=True)
    return JSONResponse(content=body)
