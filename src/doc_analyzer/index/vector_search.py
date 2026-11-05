"""Create and sync the Databricks Vector Search Delta Sync index over gold.document_chunks."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from databricks.vector_search.client import VectorSearchClient

if TYPE_CHECKING:
    from doc_analyzer.config import Settings

logger = logging.getLogger(__name__)

PRIMARY_KEY = "chunk_id"
EMBEDDING_SOURCE_COLUMN = "text"
# Columns returned with each search hit; must exist in gold.document_chunks.
INDEX_COLUMNS = ["chunk_id", "doc_id", "chunk_index", "text", "page", "source_path"]


def get_client() -> VectorSearchClient:
    """Vector Search client using the workspace's default auth."""
    return VectorSearchClient(disable_notice=True)


def ensure_endpoint(client: VectorSearchClient, settings: Settings) -> None:
    """Create the Vector Search endpoint if it does not exist."""
    existing = {e["name"] for e in client.list_endpoints().get("endpoints", [])}
    if settings.vs_endpoint in existing:
        logger.info("vector search endpoint %s exists", settings.vs_endpoint)
        return
    logger.info("creating vector search endpoint %s", settings.vs_endpoint)
    client.create_endpoint_and_wait(name=settings.vs_endpoint, endpoint_type="STANDARD")


def ensure_index(client: VectorSearchClient, settings: Settings) -> Any:
    """Create the Delta Sync index (managed embeddings, primary key chunk_id) if missing."""
    if not settings.vs_index:
        raise ValueError("VS_INDEX is not set")
    if _index_exists(client, settings):
        logger.info("vector search index %s exists", settings.vs_index)
        return client.get_index(endpoint_name=settings.vs_endpoint, index_name=settings.vs_index)

    logger.info("creating vector search index %s on %s", settings.vs_index, settings.gold_table)
    return client.create_delta_sync_index(
        endpoint_name=settings.vs_endpoint,
        index_name=settings.vs_index,
        source_table_name=settings.gold_table,
        primary_key=PRIMARY_KEY,
        pipeline_type="TRIGGERED",
        embedding_source_column=EMBEDDING_SOURCE_COLUMN,
        embedding_model_endpoint_name=settings.embedding_endpoint,
        columns_to_sync=INDEX_COLUMNS,
    )


def sync_index(client: VectorSearchClient, settings: Settings) -> None:
    """Trigger a sync of the index from the gold table's change feed."""
    index = client.get_index(endpoint_name=settings.vs_endpoint, index_name=settings.vs_index)
    if not index.describe().get("status", {}).get("ready", False):
        # A newly created index runs its initial sync on its own; sync() would fail meanwhile.
        logger.info("index %s not ready yet; skipping manual sync", settings.vs_index)
        return
    index.sync()
    logger.info("sync triggered for %s", settings.vs_index)


def wait_until_ready(client: VectorSearchClient, settings: Settings, timeout_s: int = 1800) -> None:
    """Block until the index reports ONLINE or the timeout passes.

    Also waits for a running sync to finish, so the index reflects the latest gold table.
    """
    index = client.get_index(endpoint_name=settings.vs_endpoint, index_name=settings.vs_index)
    index.wait_until_ready(timeout=timedelta(seconds=timeout_s), wait_for_updates=True)
    logger.info("index %s is ready", settings.vs_index)


def _index_exists(client: VectorSearchClient, settings: Settings) -> bool:
    indexes = client.list_indexes(settings.vs_endpoint).get("vector_indexes", [])
    return any(i.get("name") == settings.vs_index for i in indexes)
