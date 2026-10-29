"""ADLS landing container → bronze.documents_raw via Auto Loader."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.streaming import StreamingQuery

    from doc_analyzer.config import Settings


def read_landing_stream(spark: SparkSession, settings: Settings) -> DataFrame:
    """readStream with cloudFiles (binaryFile format) over settings.landing_path."""
    # TODO: implement
    raise NotImplementedError


def write_bronze(df: DataFrame, settings: Settings) -> StreamingQuery:
    """Append the stream to the bronze table with trigger(availableNow=True)."""
    # TODO: implement
    raise NotImplementedError


def run_bronze_ingest(spark: SparkSession, settings: Settings) -> None:
    """Run one availableNow ingest of new files and wait for it to finish."""
    # TODO: implement
    raise NotImplementedError
