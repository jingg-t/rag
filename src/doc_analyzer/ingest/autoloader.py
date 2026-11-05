"""ADLS landing container → bronze.documents_raw via Auto Loader."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyspark.sql import functions as F

from doc_analyzer.ingest.pipeline import ensure_tables

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.streaming.query import StreamingQuery

    from doc_analyzer.config import Settings

logger = logging.getLogger(__name__)


def to_bronze_columns(df: DataFrame) -> DataFrame:
    """binaryFile columns (path, modificationTime, length, content) → bronze table columns."""
    return df.select(
        "path",
        "content",
        "length",
        F.col("modificationTime").alias("modification_time"),
        F.current_timestamp().alias("ingest_ts"),
    )


def read_landing_stream(spark: SparkSession, settings: Settings) -> DataFrame:
    """readStream with cloudFiles (binaryFile format) over settings.landing_path."""
    if not settings.landing_path:
        raise ValueError("LANDING_PATH is not set")
    stream = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "binaryFile")
        # Re-uploading a file under the same name must be ingested again (new content).
        .option("cloudFiles.allowOverwrites", "true")
        .load(settings.landing_path)
    )
    return to_bronze_columns(stream)


def write_bronze(df: DataFrame, settings: Settings) -> StreamingQuery:
    """Append the stream to the bronze table with trigger(availableNow=True)."""
    if not settings.checkpoint_path:
        raise ValueError("CHECKPOINT_PATH is not set")
    return (
        df.writeStream.format("delta")
        .outputMode("append")
        .option("checkpointLocation", f"{settings.checkpoint_path.rstrip('/')}/bronze")
        .trigger(availableNow=True)
        .toTable(settings.bronze_table)
    )


def run_bronze_ingest(spark: SparkSession, settings: Settings) -> None:
    """Run one availableNow ingest of new files and wait for it to finish."""
    ensure_tables(spark, settings)
    query = write_bronze(read_landing_stream(spark, settings), settings)
    query.awaitTermination()
    progress = query.lastProgress
    rows = progress["numInputRows"] if progress else 0
    logger.info("bronze ingest finished: %s new files into %s", rows, settings.bronze_table)
