"""Environment-specific settings. All catalog/schema/endpoint names come from here."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    catalog: str
    schema_bronze: str = "bronze"
    schema_silver: str = "silver"
    schema_gold: str = "gold"
    landing_path: str = ""
    checkpoint_path: str = ""
    vs_endpoint: str = "doc-analyzer-vs"
    vs_index: str = ""
    embedding_endpoint: str = "databricks-gte-large-en"
    llm_endpoint: str = ""
    top_k: int = 5
    chunk_tokens: int = 512
    chunk_overlap: int = 64

    @classmethod
    def from_env(cls, overrides: Mapping[str, str] | None = None) -> Settings:
        """Build settings from environment variables, with job params / widgets as overrides."""
        # TODO: implement
        raise NotImplementedError

    @property
    def bronze_table(self) -> str:
        """Fully qualified name of bronze.documents_raw."""
        # TODO: implement
        raise NotImplementedError

    @property
    def silver_table(self) -> str:
        """Fully qualified name of silver.documents_parsed."""
        # TODO: implement
        raise NotImplementedError

    @property
    def gold_table(self) -> str:
        """Fully qualified name of gold.document_chunks."""
        # TODO: implement
        raise NotImplementedError
