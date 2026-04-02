from __future__ import annotations

from functools import lru_cache
from typing import Final, FrozenSet

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Qdrant collection slugs; PDFs live under data/sources/<SOURCES_CORPUS_FOLDER>/<slug>/
ALLOWED_COLLECTIONS: Final[FrozenSet[str]] = frozenset(
    {
        "training",
        "running",
        "tactics",
        "football",
        "basketball",
        "athletics",
        "swimming",
        "tennis",
        "volleyball",
    }
)

# Chat still sends this as `sport`; values are any allowed collection slug.
ALLOWED_SPORTS: Final[FrozenSet[str]] = ALLOWED_COLLECTIONS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nvidia_api_key: str
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    nvidia_llm_model: str = "meta/llama-3.1-8b-instruct"

    neo4j_enabled: bool = Field(default=False, validation_alias="NEO4J_ENABLED")
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    @field_validator("neo4j_enabled", mode="before")
    @classmethod
    def _parse_neo4j_enabled(cls, value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("", "0", "false", "no", "off"):
                return False
            if normalized in ("1", "true", "yes", "on"):
                return True
        return bool(value)

    qdrant_path: str = "./qdrant_storage"
    qdrant_vector_size: int = 1024
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "coachmind"

    sources_root: str = "data/sources"
    sources_corpus_folder: str = Field(
        default="foreign-sports-training-books",
        validation_alias="SOURCES_CORPUS_FOLDER",
    )

    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 50
    rag_top_k: int = Field(default=5, validation_alias="RAG_TOP_K")

    http_timeout_override_seconds: float = Field(
        default=120.0, validation_alias="HTTP_TIMEOUT_SECONDS"
    )

    def nim_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type": "application/json",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
