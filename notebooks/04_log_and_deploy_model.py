# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Log the RAG model to Unity Catalog and deploy to Model Serving

# COMMAND ----------

from doc_analyzer.config import Settings
from doc_analyzer.rag.model import log_model

# TODO: read job params / widgets into overrides
settings = Settings.from_env()
model_uri = log_model(settings, registered_model_name=f"{settings.catalog}.gold.rag_model")
print(model_uri)
