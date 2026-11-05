"""Explicit Spark schemas for each medallion table."""

from __future__ import annotations

from pyspark.sql.types import (
    ArrayType,
    BinaryType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# One entry per page: the page's character range in silver.text ([start, end), 1-indexed page).
PAGE_MAP_TYPE = ArrayType(
    StructType(
        [
            StructField("page_number", IntegerType(), nullable=False),
            StructField("start", IntegerType(), nullable=False),
            StructField("end", IntegerType(), nullable=False),
        ]
    )
)


def bronze_schema() -> StructType:
    """bronze.documents_raw: path, content, length, modification_time, ingest_ts."""
    return StructType(
        [
            StructField("path", StringType(), nullable=False),
            StructField("content", BinaryType()),
            StructField("length", LongType()),
            StructField("modification_time", TimestampType()),
            StructField("ingest_ts", TimestampType()),
        ]
    )


def silver_columns_schema() -> StructType:
    """Columns produced by pipeline.parse_partitions (silver without parsed_ts)."""
    return StructType(
        [
            StructField("doc_id", StringType(), nullable=False),
            StructField("source_path", StringType()),
            StructField("title", StringType()),
            StructField("text", StringType()),
            StructField("page_map", PAGE_MAP_TYPE),
            StructField("mime_type", StringType()),
            StructField("parse_status", StringType()),  # 'ok' | 'error'
            StructField("parse_error", StringType()),
        ]
    )


def silver_schema() -> StructType:
    """silver.documents_parsed: doc_id, source_path, title, text, page_map, mime_type,
    parse_status, parse_error, parsed_ts."""
    return StructType([*silver_columns_schema().fields, StructField("parsed_ts", TimestampType())])


def gold_schema() -> StructType:
    """gold.document_chunks: chunk_id, doc_id, chunk_index, text, page, source_path, token_count."""
    return StructType(
        [
            StructField("chunk_id", StringType(), nullable=False),
            StructField("doc_id", StringType(), nullable=False),
            StructField("chunk_index", IntegerType(), nullable=False),
            StructField("text", StringType()),
            StructField("page", IntegerType()),
            StructField("source_path", StringType()),
            StructField("token_count", IntegerType()),
        ]
    )
