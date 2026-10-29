"""Similarity search over the Vector Search index."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from doc_analyzer.config import Settings
    from doc_analyzer.rag.types import RetrievedChunk


class Retriever(Protocol):
    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]: ...


class VectorSearchRetriever:
    """Retriever backed by the Databricks Vector Search Delta Sync index."""

    def __init__(self, settings: Settings) -> None:
        # TODO: implement
        raise NotImplementedError

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        """Top-k chunks for the query, most similar first."""
        # TODO: implement
        raise NotImplementedError
