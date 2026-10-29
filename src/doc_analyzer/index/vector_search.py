"""Create and sync the Databricks Vector Search Delta Sync index over gold.document_chunks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from databricks.vector_search.client import VectorSearchClient

    from doc_analyzer.config import Settings


def get_client() -> VectorSearchClient:
    """Vector Search client using the workspace's default auth."""
    # TODO: implement
    raise NotImplementedError


def ensure_endpoint(client: VectorSearchClient, settings: Settings) -> None:
    """Create the Vector Search endpoint if it does not exist."""
    # TODO: implement
    raise NotImplementedError


def ensure_index(client: VectorSearchClient, settings: Settings) -> Any:
    """Create the Delta Sync index (managed embeddings, primary key chunk_id) if missing."""
    # TODO: implement
    raise NotImplementedError


def sync_index(client: VectorSearchClient, settings: Settings) -> None:
    """Trigger a sync of the index from the gold table's change feed."""
    # TODO: implement
    raise NotImplementedError


def wait_until_ready(client: VectorSearchClient, settings: Settings, timeout_s: int = 1800) -> None:
    """Block until the index reports ONLINE or the timeout passes."""
    # TODO: implement
    raise NotImplementedError
