# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Log the RAG model to Unity Catalog and deploy to Model Serving

# COMMAND ----------

from doc_analyzer.config import Settings
from doc_analyzer.rag.model import deploy_endpoint, log_model

overrides = {k.upper(): v for k, v in dbutils.widgets.getAll().items()}  # noqa: F821
settings = Settings.from_env(overrides)
model_name = f"{settings.catalog}.{settings.schema_gold}.rag_model"
version = log_model(settings, registered_model_name=model_name)
deploy_endpoint(dbutils.widgets.get("serving_endpoint"), model_name, version)  # noqa: F821
