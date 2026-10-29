"""Explicit Spark schemas for each medallion table."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql.types import StructType


def bronze_schema() -> StructType:
    """bronze.documents_raw: path, content, length, modification_time, ingest_ts."""
    # TODO: implement
    raise NotImplementedError


def silver_schema() -> StructType:
    """silver.documents_parsed: doc_id, source_path, title, text, page_map, mime_type,
    parse_status, parse_error."""
    # TODO: implement
    raise NotImplementedError


def gold_schema() -> StructType:
    """gold.document_chunks: chunk_id, doc_id, chunk_index, text, page, source_path, token_count."""
    # TODO: implement
    raise NotImplementedError
