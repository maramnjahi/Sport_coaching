from __future__ import annotations

import logging
from typing import Optional

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)

_driver: Optional[AsyncDriver] = None


def neo4j_driver_ready() -> bool:
    return _driver is not None


async def init_neo4j(uri: str, user: str, password: str) -> bool:
    """Connect to Neo4j. Returns False if the server is unreachable (app may still run)."""
    global _driver
    _driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        await _driver.verify_connectivity()
        return True
    except ServiceUnavailable as exc:
        logger.warning(
            "Neo4j enabled but not reachable at %s; graph features disabled. Start Neo4j or set NEO4J_ENABLED=false. (%s)",
            uri,
            exc,
        )
        await _driver.close()
        _driver = None
        return False


async def shutdown_neo4j() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


def get_neo4j() -> AsyncDriver:
    if _driver is None:
        raise RuntimeError("Neo4j AsyncDriver is not initialized")
    return _driver
