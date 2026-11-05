# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Ingest: ADLS landing → bronze

# COMMAND ----------

from doc_analyzer.config import Settings
from doc_analyzer.ingest.autoloader import run_bronze_ingest

overrides = {k.upper(): v for k, v in dbutils.widgets.getAll().items()}  # noqa: F821
settings = Settings.from_env(overrides)
run_bronze_ingest(spark, settings)  # noqa: F821
