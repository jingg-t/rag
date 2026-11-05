"""Spark jobs wiring parse/chunk into silver and gold with idempotent MERGEs."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import pandas as pd
from pyspark.sql import Window
from pyspark.sql import functions as F

from doc_analyzer.ingest.chunk import chunk_pages, make_chunk_id
from doc_analyzer.ingest.parse import Page, compute_doc_id, parse_document
from doc_analyzer.ingest.schemas import (
    bronze_schema,
    gold_schema,
    silver_columns_schema,
    silver_schema,
)

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.types import StructType

    from doc_analyzer.config import Settings

logger = logging.getLogger(__name__)

# Rows per Arrow batch sent to Python. Bronze rows carry whole files, so keep this small.
PARSE_BATCH_ROWS = 16
CHUNK_BATCH_ROWS = 64

_SILVER_COLUMNS = silver_columns_schema().fieldNames()
_GOLD_COLUMNS = gold_schema().fieldNames()


def ensure_tables(spark: SparkSession, settings: Settings) -> None:
    """Create catalog schemas and Delta tables if missing (gold with Change Data Feed on)."""
    tables: list[tuple[str, str, StructType, dict[str, str]]] = [
        (settings.schema_bronze, settings.bronze_table, bronze_schema(), {}),
        (settings.schema_silver, settings.silver_table, silver_schema(), {}),
        (
            settings.schema_gold,
            settings.gold_table,
            gold_schema(),
            {"delta.enableChangeDataFeed": "true"},
        ),
    ]
    for schema_name, table, schema, properties in tables:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {settings.catalog}.{schema_name}")
        columns = ", ".join(
            f"`{f.name}` {f.dataType.simpleString()}{'' if f.nullable else ' NOT NULL'}"
            for f in schema.fields
        )
        table_properties = ", ".join(f"'{k}' = '{v}'" for k, v in properties.items())
        spark.sql(
            f"CREATE TABLE IF NOT EXISTS {table} ({columns}) USING DELTA"
            + (f" TBLPROPERTIES ({table_properties})" if table_properties else "")
        )
    logger.info("tables ready in catalog %s", settings.catalog)


def parse_partitions(batches: Iterable[pd.DataFrame]) -> Iterator[pd.DataFrame]:
    """mapInPandas: bronze rows → silver rows. Parse failures become parse_status='error'."""
    for batch in batches:
        rows = [
            _parse_row(path, bytes(content))
            for path, content in zip(batch["path"], batch["content"], strict=True)
        ]
        yield pd.DataFrame(rows, columns=_SILVER_COLUMNS)


def chunk_partitions(
    batches: Iterable[pd.DataFrame],
    chunk_tokens: int,
    overlap: int,
) -> Iterator[pd.DataFrame]:
    """mapInPandas: silver rows → gold chunk rows."""
    for batch in batches:
        rows: list[dict[str, Any]] = []
        for doc_id, source_path, text, page_map in zip(
            batch["doc_id"], batch["source_path"], batch["text"], batch["page_map"], strict=True
        ):
            pages = [
                Page(int(p["page_number"]), text[int(p["start"]) : int(p["end"])]) for p in page_map
            ]
            for chunk in chunk_pages(pages, chunk_tokens, overlap):
                rows.append(
                    {
                        "chunk_id": make_chunk_id(doc_id, chunk.chunk_index),
                        "doc_id": doc_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "page": chunk.page,
                        "source_path": source_path,
                        "token_count": chunk.token_count,
                    }
                )
        yield pd.DataFrame(rows, columns=_GOLD_COLUMNS)


def merge_into(
    spark: SparkSession,
    source: DataFrame,
    target_table: str,
    keys: Sequence[str],
) -> None:
    """MERGE source into target on keys (update matched, insert unmatched)."""
    if not keys:
        raise ValueError("merge_into needs at least one key column")
    condition = " AND ".join(f"t.`{k}` = s.`{k}`" for k in keys)
    source.dropDuplicates(list(keys)).createOrReplaceTempView("_merge_source")
    spark.sql(
        f"MERGE INTO {target_table} t USING _merge_source s ON {condition} "
        "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *"
    )


def build_silver(spark: SparkSession, settings: Settings) -> None:
    """Parse new/changed bronze documents and MERGE into silver on doc_id.

    Only documents whose doc_id is not in silver yet are parsed, so a re-run parses nothing.
    Silver rows that no longer match the latest bronze version of any file (the file was
    re-uploaded with new content) are deleted.
    """
    current = _current_documents(spark, settings)
    silver = spark.table(settings.silver_table)

    new_docs = current.join(silver.select("doc_id"), "doc_id", "left_anti").select(
        "path", "content"
    )
    with _arrow_batch_rows(spark, PARSE_BATCH_ROWS):
        parsed = new_docs.mapInPandas(parse_partitions, silver_columns_schema()).withColumn(
            "parsed_ts", F.current_timestamp()
        )
        merge_into(spark, parsed, settings.silver_table, ["doc_id"])

    _delete_not_in(spark, settings.silver_table, "doc_id", current.select("doc_id"))
    logger.info("silver built: %s", settings.silver_table)


def build_gold(spark: SparkSession, settings: Settings) -> None:
    """Chunk new/changed silver documents and MERGE into gold on chunk_id; drop stale chunks.

    Only parsed documents without chunks are chunked. Changing chunk_tokens or chunk_overlap
    does not re-chunk existing documents: truncate gold and re-run to rebuild it.
    """
    ok_docs = spark.table(settings.silver_table).where(F.col("parse_status") == "ok")
    gold = spark.table(settings.gold_table)

    to_chunk = ok_docs.join(gold.select("doc_id").distinct(), "doc_id", "left_anti").select(
        "doc_id", "source_path", "text", "page_map"
    )

    def chunker(batches: Iterable[pd.DataFrame]) -> Iterator[pd.DataFrame]:
        return chunk_partitions(batches, settings.chunk_tokens, settings.chunk_overlap)

    with _arrow_batch_rows(spark, CHUNK_BATCH_ROWS):
        chunks = to_chunk.mapInPandas(chunker, gold_schema())
        merge_into(spark, chunks, settings.gold_table, ["chunk_id"])

    _delete_not_in(spark, settings.gold_table, "doc_id", ok_docs.select("doc_id"))
    logger.info("gold built: %s", settings.gold_table)


def propagate_deletes(spark: SparkSession, settings: Settings, allow_empty: bool = False) -> None:
    """Delete silver/gold rows whose source file no longer exists in the landing path.

    Bronze rows of deleted files are removed too, so the next build_silver does not bring
    them back. The gold deletes reach the Vector Search index through Change Data Feed.

    Args:
        allow_empty: Allow deleting everything when the landing path lists no files. Off by
            default, so a wrong or temporarily empty path cannot wipe the tables.

    Raises:
        RuntimeError: If the landing path has no files, bronze is not empty and allow_empty
            is False.
    """
    existing = (
        spark.read.format("binaryFile")
        .option("recursiveFileLookup", "true")
        .load(settings.landing_path)
        .select("path")
    )
    if existing.isEmpty() and not spark.table(settings.bronze_table).isEmpty():
        if not allow_empty:
            raise RuntimeError(
                f"no files found under {settings.landing_path}; refusing to delete all "
                "documents (pass allow_empty=True if this is intended)"
            )
        logger.warning("landing path is empty; deleting all documents")

    _delete_not_in(spark, settings.bronze_table, "path", existing)
    _delete_not_in(spark, settings.silver_table, "source_path", existing)
    _delete_not_in(spark, settings.gold_table, "source_path", existing)
    logger.info("deletes propagated from %s", settings.landing_path)


def _delete_not_in(spark: SparkSession, table: str, column: str, keep: DataFrame) -> None:
    """Delete rows of table whose column value is not in keep's single column.

    Uses MERGE because Delta's DELETE does not support subqueries.
    """
    keep.toDF("_key").distinct().createOrReplaceTempView("_keep")
    spark.sql(
        f"MERGE INTO {table} t USING _keep s ON t.`{column}` = s._key "
        "WHEN NOT MATCHED BY SOURCE THEN DELETE"
    )


def _parse_row(path: str, content: bytes) -> dict[str, Any]:
    row: dict[str, Any] = {
        "doc_id": compute_doc_id(content),
        "source_path": path,
        "title": None,
        "text": None,
        "page_map": [],
        "mime_type": None,
        "parse_status": "ok",
        "parse_error": None,
    }
    try:
        doc = parse_document(path, content)
    except Exception as e:  # a bad file must not fail the batch
        logger.warning("failed to parse %s: %s", path, e)
        row.update(parse_status="error", parse_error=f"{type(e).__name__}: {e}")
        return row

    page_map = []
    offset = 0
    for page in doc.pages:
        page_map.append(
            {"page_number": page.page_number, "start": offset, "end": offset + len(page.text)}
        )
        offset += len(page.text) + 2  # ParsedDocument.text joins pages with "\n\n"
    row.update(title=doc.title, text=doc.text, page_map=page_map, mime_type=doc.mime_type)
    return row


def _current_documents(spark: SparkSession, settings: Settings) -> DataFrame:
    """Latest bronze version of each file, one row per doc_id (identical files deduplicated)."""
    latest_per_path = Window.partitionBy("path").orderBy(
        F.col("modification_time").desc(), F.col("ingest_ts").desc()
    )
    latest_per_doc = Window.partitionBy("doc_id").orderBy(
        F.col("modification_time").desc(), F.col("path")
    )
    return (
        spark.table(settings.bronze_table)
        .withColumn("_rn", F.row_number().over(latest_per_path))
        .where("_rn = 1")
        .withColumn("doc_id", F.sha2(F.col("content"), 256))
        .withColumn("_rn", F.row_number().over(latest_per_doc))
        .where("_rn = 1")
        .drop("_rn")
    )


@contextmanager
def _arrow_batch_rows(spark: SparkSession, rows: int) -> Iterator[None]:
    """Temporarily cap the rows per Arrow batch handed to mapInPandas."""
    key = "spark.sql.execution.arrow.maxRecordsPerBatch"
    previous = spark.conf.get(key)
    spark.conf.set(key, str(rows))
    try:
        yield
    finally:
        if previous is None:
            spark.conf.unset(key)
        else:
            spark.conf.set(key, previous)
