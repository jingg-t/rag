"""Environment-specific settings. All catalog/schema/endpoint names come from here."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any, get_type_hints


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
        """Build settings from environment variables, with job params / widgets as overrides.

        Each field is read from its upper-case name (catalog → CATALOG, top_k → TOP_K).
        Missing or empty values keep the field default.

        Raises:
            ValueError: If CATALOG is not set, or an int setting is not a number.
        """
        values = {**os.environ, **(overrides or {})}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            raw = values.get(f.name.upper(), "").strip()
            if not raw:
                continue
            if hints[f.name] is int:
                try:
                    kwargs[f.name] = int(raw)
                except ValueError as e:
                    raise ValueError(f"{f.name.upper()} must be an integer, got {raw!r}") from e
            else:
                kwargs[f.name] = raw
        if "catalog" not in kwargs:
            raise ValueError("CATALOG is not set")
        return cls(**kwargs)

    @property
    def bronze_table(self) -> str:
        """Fully qualified name of bronze.documents_raw."""
        return f"{self.catalog}.{self.schema_bronze}.documents_raw"

    @property
    def silver_table(self) -> str:
        """Fully qualified name of silver.documents_parsed."""
        return f"{self.catalog}.{self.schema_silver}.documents_parsed"

    @property
    def gold_table(self) -> str:
        """Fully qualified name of gold.document_chunks."""
        return f"{self.catalog}.{self.schema_gold}.document_chunks"
