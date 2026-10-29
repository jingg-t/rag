"""Spark jobs wiring parse/chunk into silver and gold with idempotent MERGEs."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from pyspark.sql import DataFrame, SparkSession

    from doc_analyzer.config import Settings


def ensure_tables(spark: SparkSession, settings: Settings) -> None:
    """Create catalog schemas and Delta tables if missing (gold with Change Data Feed on)."""
    # TODO: implement
    raise NotImplementedError


def parse_partitions(batches: Iterator[pd.DataFrame]) -> Iterator[pd.DataFrame]:
    """mapInPandas: bronze rows → silver rows. Parse failures become parse_status='error'."""
    # TODO: implement
    raise NotImplementedError


def chunk_partitions(
    batches: Iterator[pd.DataFrame],
    chunk_tokens: int,
    overlap: int,
) -> Iterator[pd.DataFrame]:
    """mapInPandas: silver rows → gold chunk rows."""
    # TODO: implement
    raise NotImplementedError


def merge_into(
    spark: SparkSession,
    source: DataFrame,
    target_table: str,
    keys: Sequence[str],
) -> None:
    """MERGE source into target on keys (update matched, insert unmatched)."""
    # TODO: implement
    raise NotImplementedError


def build_silver(spark: SparkSession, settings: Settings) -> None:
    """Parse new/changed bronze documents and MERGE into silver on doc_id."""
    # TODO: implement
    raise NotImplementedError


def build_gold(spark: SparkSession, settings: Settings) -> None:
    """Chunk new/changed silver documents and MERGE into gold on chunk_id; drop stale chunks."""
    # TODO: implement
    raise NotImplementedError


def propagate_deletes(spark: SparkSession, settings: Settings) -> None:
    """Delete silver/gold rows whose source file no longer exists in the landing path."""
    # TODO: implement
    raise NotImplementedError
