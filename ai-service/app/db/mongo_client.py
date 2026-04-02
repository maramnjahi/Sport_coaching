from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient[Any] | None = None
_database: AsyncIOMotorDatabase[Any] | None = None


def init_mongo(uri: str, database: str) -> None:
    global _client, _database
    _client = AsyncIOMotorClient(uri)
    _database = _client[database]


async def shutdown_mongo() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def get_mongo_database() -> AsyncIOMotorDatabase[Any]:
    if _database is None:
        raise RuntimeError("MongoDB client is not initialized")
    return _database
