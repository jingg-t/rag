from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from doc_analyzer.config import Settings
from doc_analyzer.ingest.autoloader import to_bronze_columns
from doc_analyzer.ingest.parse import compute_doc_id
from doc_analyzer.ingest.pipeline import (
    build_gold,
    build_silver,
    ensure_tables,
    propagate_deletes,
)

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parents[1] / "fixtures"
HANDBOOK = "# Handbook\n\n" + " ".join(f"Policy sentence number {i}." for i in range(150))
FAQ = "Support is available on weekdays from nine to five."


@pytest.fixture
def settings(spark: SparkSession, tmp_path: Path) -> Iterator[Settings]:
    """Fresh schemas per test, landing path in a temp folder."""
    suffix = uuid.uuid4().hex[:8]
    landing = tmp_path / "landing"
    landing.mkdir()
    s = Settings(
        catalog="spark_catalog",
        schema_bronze=f"bronze_{suffix}",
        schema_silver=f"silver_{suffix}",
        schema_gold=f"gold_{suffix}",
        landing_path=landing.as_uri(),
        chunk_tokens=64,
        chunk_overlap=8,
    )
    ensure_tables(spark, s)
    yield s
    for schema in (s.schema_bronze, s.schema_silver, s.schema_gold):
        spark.sql(f"DROP SCHEMA IF EXISTS spark_catalog.{schema} CASCADE")


def _landing(settings: Settings) -> Path:
    return Path(settings.landing_path.removeprefix("file:///").removeprefix("file://"))


def _upload(settings: Settings, name: str, content: bytes) -> None:
    (_landing(settings) / name).write_bytes(content)


def _ingest(spark: SparkSession, settings: Settings) -> None:
    """Batch stand-in for Auto Loader: append every landing file to bronze."""
    files = spark.read.format("binaryFile").load(settings.landing_path)
    to_bronze_columns(files).write.format("delta").mode("append").saveAsTable(settings.bronze_table)


def _run_pipeline(spark: SparkSession, settings: Settings) -> None:
    build_silver(spark, settings)
    build_gold(spark, settings)
    propagate_deletes(spark, settings)


def _counts(spark: SparkSession, settings: Settings) -> tuple[int, int]:
    return spark.table(settings.silver_table).count(), spark.table(settings.gold_table).count()


def test_pipeline_is_idempotent_on_rerun(spark: SparkSession, settings: Settings) -> None:
    _upload(settings, "handbook.md", HANDBOOK.encode())
    _upload(settings, "faq.txt", FAQ.encode())
    _upload(settings, "sample.pdf", (FIXTURES / "pdf-sample_0.pdf").read_bytes())
    _ingest(spark, settings)

    _run_pipeline(spark, settings)
    first = _counts(spark, settings)
    first_chunk_ids = {r.chunk_id for r in spark.table(settings.gold_table).collect()}
    _run_pipeline(spark, settings)

    assert first[0] == 3
    assert first[1] > 3  # the handbook spans several chunks
    assert _counts(spark, settings) == first
    assert {r.chunk_id for r in spark.table(settings.gold_table).collect()} == first_chunk_ids


def test_gold_chunks_point_back_to_silver(spark: SparkSession, settings: Settings) -> None:
    _upload(settings, "handbook.md", HANDBOOK.encode())
    _ingest(spark, settings)
    _run_pipeline(spark, settings)

    doc_id = compute_doc_id(HANDBOOK.encode())
    silver = spark.table(settings.silver_table).collect()
    gold = spark.table(settings.gold_table).orderBy("chunk_index").collect()

    assert [r.doc_id for r in silver] == [doc_id]
    assert silver[0].title == "Handbook"
    assert silver[0].mime_type == "text/markdown"
    assert [r.chunk_id for r in gold] == [f"{doc_id}:{i}" for i in range(len(gold))]
    assert all(r.page == 1 and r.source_path.endswith("handbook.md") for r in gold)
    assert all(0 < r.token_count <= settings.chunk_tokens for r in gold)


def test_reuploaded_file_does_not_duplicate_rows(spark: SparkSession, settings: Settings) -> None:
    _upload(settings, "faq.txt", FAQ.encode())
    _ingest(spark, settings)
    _run_pipeline(spark, settings)
    before = _counts(spark, settings)

    _ingest(spark, settings)  # same file arrives again: bronze gets a second row
    _run_pipeline(spark, settings)

    assert spark.table(settings.bronze_table).count() == 2
    assert _counts(spark, settings) == before


def test_changed_file_replaces_old_version(spark: SparkSession, settings: Settings) -> None:
    _upload(settings, "faq.txt", FAQ.encode())
    _ingest(spark, settings)
    _run_pipeline(spark, settings)

    new_text = "Support is now available every day."
    _upload(settings, "faq.txt", new_text.encode())
    _ingest(spark, settings)  # bronze now holds both versions; the newer one must win
    _run_pipeline(spark, settings)

    silver = spark.table(settings.silver_table).collect()
    gold = spark.table(settings.gold_table).collect()
    assert [r.doc_id for r in silver] == [compute_doc_id(new_text.encode())]
    assert [r.text for r in gold] == [new_text]


def test_parse_failure_is_recorded_not_raised(spark: SparkSession, settings: Settings) -> None:
    _upload(settings, "broken.pdf", b"%PDF-1.7 truncated garbage")
    _upload(settings, "faq.txt", FAQ.encode())
    _ingest(spark, settings)

    _run_pipeline(spark, settings)

    rows = {
        r.source_path.rsplit("/", 1)[-1]: r for r in spark.table(settings.silver_table).collect()
    }
    assert rows["broken.pdf"].parse_status == "error"
    assert rows["broken.pdf"].parse_error
    assert rows["faq.txt"].parse_status == "ok"
    gold_paths = {r.source_path for r in spark.table(settings.gold_table).collect()}
    assert all(p.endswith("faq.txt") for p in gold_paths)


def test_deleted_source_file_removes_silver_and_gold_rows(
    spark: SparkSession, settings: Settings
) -> None:
    _upload(settings, "handbook.md", HANDBOOK.encode())
    _upload(settings, "faq.txt", FAQ.encode())
    _ingest(spark, settings)
    _run_pipeline(spark, settings)

    (_landing(settings) / "handbook.md").unlink()
    _run_pipeline(spark, settings)

    for table, column in [
        (settings.bronze_table, "path"),
        (settings.silver_table, "source_path"),
        (settings.gold_table, "source_path"),
    ]:
        paths = {r[0] for r in spark.table(table).select(column).collect()}
        assert paths and all(p.endswith("faq.txt") for p in paths), table


def test_empty_landing_path_refuses_to_delete_everything(
    spark: SparkSession, settings: Settings
) -> None:
    _upload(settings, "faq.txt", FAQ.encode())
    _ingest(spark, settings)
    _run_pipeline(spark, settings)

    (_landing(settings) / "faq.txt").unlink()

    with pytest.raises(RuntimeError):
        propagate_deletes(spark, settings)
    assert spark.table(settings.silver_table).count() == 1


def test_gold_has_change_data_feed(spark: SparkSession, settings: Settings) -> None:
    props = {
        r.key: r.value for r in spark.sql(f"SHOW TBLPROPERTIES {settings.gold_table}").collect()
    }
    assert props.get("delta.enableChangeDataFeed") == "true"
