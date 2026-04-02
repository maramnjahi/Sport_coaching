from __future__ import annotations

from typing import Any, Mapping

from neo4j import AsyncManagedTransaction

from app.config import ALLOWED_COLLECTIONS, Settings
from app.db.neo4j_client import get_neo4j, neo4j_driver_ready


class GraphService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _graph_active(self) -> bool:
        return self._settings.neo4j_enabled and neo4j_driver_ready()

    async def ensure_domain_nodes(self) -> None:
        if not self._graph_active():
            return
        driver = get_neo4j()
        async with driver.session(database=self._settings.neo4j_database) as session:
            for name in sorted(ALLOWED_COLLECTIONS):
                result = await session.run(
                    "MERGE (k:KnowledgeDomain {name: $name})",
                    {"name": name},
                )
                await result.consume()

    async def merge_source_document_graph(
        self,
        *,
        domain: str,
        filename: str,
        document_id: str,
        chunk_count: int,
        entities: list[dict[str, str]],
    ) -> None:
        if not self._graph_active():
            return
        await self.run_write(
            (
                "MERGE (k:KnowledgeDomain {name: $domain}) "
                "MERGE (d:SourceDocument {document_id: $document_id, domain: $domain}) "
                "SET d.filename = $filename, d.chunk_count = $chunk_count "
                "MERGE (k)-[:HAS_DOCUMENT]->(d)"
            ),
            {
                "domain": domain,
                "filename": filename,
                "document_id": document_id,
                "chunk_count": chunk_count,
            },
        )
        if not entities:
            return
        await self.run_write(
            (
                "MATCH (d:SourceDocument {document_id: $document_id, domain: $domain}) "
                "UNWIND $entities AS ent "
                "MERGE (e:CoachingEntity {name: ent.name, domain: $domain}) "
                "SET e.kind = ent.kind "
                "MERGE (d)-[:MENTIONS]->(e)"
            ),
            {
                "domain": domain,
                "document_id": document_id,
                "entities": entities,
            },
        )

    async def run_read(
        self,
        cypher: str,
        parameters: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        if not self._graph_active():
            return []
        driver = get_neo4j()

        async def work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
            result = await tx.run(cypher, dict(parameters))
            rows: list[dict[str, Any]] = []
            async for record in result:
                rows.append(record.data())
            return rows

        async with driver.session(database=self._settings.neo4j_database) as session:
            return await session.execute_read(work)

    async def run_write(
        self,
        cypher: str,
        parameters: Mapping[str, Any],
    ) -> None:
        if not self._graph_active():
            return
        driver = get_neo4j()

        async def work(tx: AsyncManagedTransaction) -> None:
            result = await tx.run(cypher, dict(parameters))
            await result.consume()

        async with driver.session(database=self._settings.neo4j_database) as session:
            await session.execute_write(work)

    async def query_related_entities(self, query: str, domain: str) -> str:
        if not self._graph_active():
            return ""
        needle = query.strip().lower()[:120]
        rows = await self.run_read(
            (
                "MATCH (k:KnowledgeDomain {name: $domain})-[:HAS_DOCUMENT]->(d:SourceDocument) "
                "OPTIONAL MATCH (d)-[:MENTIONS]->(e:CoachingEntity) "
                "WHERE $needle = '' OR toLower(coalesce(e.name,'')) CONTAINS $needle "
                "   OR toLower(coalesce(d.filename,'')) CONTAINS $needle "
                "RETURN e.name AS entity, e.kind AS entity_type, d.filename AS source "
                "LIMIT 20"
            ),
            {"domain": domain, "needle": needle},
        )
        if not rows:
            return ""
        entities: list[str] = []
        sources: list[str] = []
        seen_entities: set[str] = set()
        seen_sources: set[str] = set()
        for row in rows:
            entity = str(row.get("entity") or "").strip()
            entity_type = str(row.get("entity_type") or "").strip()
            source = str(row.get("source") or "").strip()
            if entity:
                label = f"{entity} ({entity_type})" if entity_type else entity
                if label not in seen_entities:
                    seen_entities.add(label)
                    entities.append(label)
            if source and source not in seen_sources:
                seen_sources.add(source)
                sources.append(source)
        if not entities and not sources:
            return ""
        entities_blob = ", ".join(entities)
        sources_blob = ", ".join(sources)
        return f"Entities: [{entities_blob}] | Sources: [{sources_blob}]"
