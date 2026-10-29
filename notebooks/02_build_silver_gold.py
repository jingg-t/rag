# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Parse and chunk: bronze → silver → gold

# COMMAND ----------

from doc_analyzer.config import Settings
from doc_analyzer.ingest.pipeline import build_gold, build_silver, ensure_tables, propagate_deletes

# TODO: read job params / widgets into overrides
settings = Settings.from_env()
ensure_tables(spark, settings)  # noqa: F821
build_silver(spark, settings)  # noqa: F821
build_gold(spark, settings)  # noqa: F821
propagate_deletes(spark, settings)  # noqa: F821
