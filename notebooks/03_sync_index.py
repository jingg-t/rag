# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Vector Search: create / sync index on gold.document_chunks

# COMMAND ----------

from doc_analyzer.config import Settings
from doc_analyzer.index.vector_search import (
    ensure_endpoint,
    ensure_index,
    get_client,
    sync_index,
    wait_until_ready,
)

# TODO: read job params / widgets into overrides
settings = Settings.from_env()
client = get_client()
ensure_endpoint(client, settings)
ensure_index(client, settings)
sync_index(client, settings)
wait_until_ready(client, settings)
