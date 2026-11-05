from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark() -> Iterator[SparkSession]:
    """Local SparkSession with delta-spark configured, for integration tests.

    Skips the tests if Spark cannot start, e.g. on Windows without winutils.exe/HADOOP_HOME.
    """
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)  # workers use this venv
    warehouse = tempfile.mkdtemp(prefix="spark-warehouse-")
    builder = (
        SparkSession.builder.master("local[2]")
        .appName("doc-analyzer-tests")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        )
        .config("spark.sql.warehouse.dir", warehouse)
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={warehouse}")
    )
    try:
        session = configure_spark_with_delta_pip(builder).getOrCreate()
    except Exception as e:  # any startup failure means "no local Spark here"
        hint = " (set HADOOP_HOME to a folder with bin/winutils.exe)" if os.name == "nt" else ""
        pytest.skip(f"local Spark unavailable{hint}: {str(e).splitlines()[0]}")
    yield session
    session.stop()
