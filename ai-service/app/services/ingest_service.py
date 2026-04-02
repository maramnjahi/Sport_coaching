from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Any

import tiktoken

from app.config import ALLOWED_COLLECTIONS, Settings
from app.services.embedding_service import EmbeddingService
from app.services.graph_service import GraphService
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService
from app.utils.pdf_parser import extract_pdf_pages

_ENTITY_SYSTEM = (
    "You extract entities for a sports coaching knowledge graph from Olympic-level coaching text. "
    "Reply with ONLY a JSON array of objects, each with keys: name (string under 80 chars), "
    "kind (one of: concept, drill, rule, metric, periodization). "
    "Maximum 15 entities. No markdown fences, no commentary."
)


class IngestService:
    def __init__(
        self,
        settings: Settings,
        embedding: EmbeddingService,
        vector: VectorService,
        graph: GraphService,
        llm: LLMService,
    ) -> None:
        self._settings = settings
        self._embedding = embedding
        self._vector = vector
        self._graph = graph
        self._llm = llm
        self._encoding = tiktoken.get_encoding("cl100k_base")

    def sources_dir_for_collection(self, collection: str) -> Path:
        slug = collection.strip().lower()
        if slug not in ALLOWED_COLLECTIONS:
            raise ValueError("collection must be one of the configured slugs")
        root = Path(self._settings.sources_root)
        corpus = self._settings.sources_corpus_folder.strip().strip("/\\")
        return (root / corpus / slug).resolve()

    async def ingest_all_collections(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for slug in sorted(ALLOWED_COLLECTIONS):
            totals[slug] = await self.ingest_collection_folder(slug)
        return totals

    async def ingest_collection_folder(self, collection: str) -> int:
        sport_norm = collection.strip().lower()
        folder = self.sources_dir_for_collection(sport_norm)
        if not folder.is_dir():
            return 0
        pdf_paths = sorted(folder.glob("*.pdf"))
        total_chunks = 0
        for pdf_path in pdf_paths:
            total_chunks += await self._ingest_pdf_path(sport_norm, pdf_path)
        return total_chunks

    async def _ingest_pdf_path(self, sport: str, pdf_path: Path) -> int:
        pdf_bytes = await asyncio.to_thread(pdf_path.read_bytes)
        pages = await asyncio.to_thread(extract_pdf_pages, pdf_bytes)
        chunks = self._chunk_pages(pages)
        if not chunks:
            return 0
        filename = pdf_path.name
        document_id = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"{sport}:{filename}"),
        )
        texts = [item["text"] for item in chunks]
        vectors = await self._embed_in_batches(texts)
        payloads: list[dict[str, Any]] = []
        point_ids: list[str] = []
        for index, chunk in enumerate(chunks):
            point_ids.append(
                str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"{sport}:{filename}:{index}",
                    )
                )
            )
            payloads.append(
                {
                    "text": chunk["text"],
                    "page": chunk["page"],
                    "source": filename,
                    "document_id": document_id,
                    "sport": sport,
                }
            )
        await self._vector.upsert_chunks(
            collection=sport,
            vectors=vectors,
            payloads=payloads,
            ids=point_ids,
        )
        sample_text = "\n\n".join(texts)[:12000]
        entities = await self._extract_entities(sample_text)
        await self._graph.merge_source_document_graph(
            domain=sport,
            filename=filename,
            document_id=document_id,
            chunk_count=len(chunks),
            entities=entities,
        )
        return len(chunks)

    async def _extract_entities(self, text: str) -> list[dict[str, str]]:
        if not text.strip():
            return []
        user_content = f"Text:\n{text[:12000]}"
        raw = await self._llm.chat_completion(
            [
                {"role": "system", "content": _ENTITY_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        return self._parse_entity_json(raw)

    def _parse_entity_json(self, raw: str) -> list[dict[str, str]]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\[[\s\S]*\]", cleaned)
            if not match:
                return []
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
        if not isinstance(data, list):
            return []
        allowed_kinds = {
            "concept",
            "drill",
            "rule",
            "metric",
            "periodization",
        }
        result: list[dict[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            kind = str(item.get("kind", "concept")).strip().lower()
            if not name or len(name) > 200:
                continue
            if kind not in allowed_kinds:
                kind = "concept"
            result.append({"name": name, "kind": kind})
        return result[:15]

    def _chunk_pages(self, pages: list[tuple[int, str]]) -> list[dict[str, Any]]:
        size = self._settings.chunk_size_tokens
        overlap = self._settings.chunk_overlap_tokens
        stride = max(size - overlap, 1)
        stream: list[tuple[int, int]] = []
        for page_number, text in pages:
            for token_id in self._encoding.encode(text):
                stream.append((page_number, token_id))
        chunks: list[dict[str, Any]] = []
        index = 0
        while index < len(stream):
            window = stream[index : index + size]
            if not window:
                break
            page_start = window[0][0]
            token_ids = [token for _, token in window]
            chunk_text = self._encoding.decode(token_ids).strip()
            if chunk_text:
                chunks.append({"page": page_start, "text": chunk_text})
            index += stride
        return chunks

    async def _embed_in_batches(self, texts: list[str]) -> list[list[float]]:
        batch_size = 16
        aggregated: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            aggregated.extend(await self._embedding.embed_texts(batch))
        return aggregated
