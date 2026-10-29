# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Ingest: ADLS landing → bronze

# COMMAND ----------

from doc_analyzer.config import Settings
from doc_analyzer.ingest.autoloader import run_bronze_ingest

# TODO: read job params / widgets into overrides
settings = Settings.from_env()
run_bronze_ingest(spark, settings)  # noqa: F821
