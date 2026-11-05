"""Similarity search over the Vector Search index."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

from doc_analyzer.rag.types import RetrievedChunk

if TYPE_CHECKING:
    from doc_analyzer.config import Settings

logger = logging.getLogger(__name__)

RETRIEVE_COLUMNS = ["chunk_id", "doc_id", "text", "source_path", "page"]


class Retriever(Protocol):
    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]: ...


class SearchIndex(Protocol):
    """The part of databricks.vector_search's VectorSearchIndex used here."""

    def similarity_search(
        self, columns: list[str], query_text: str, num_results: int
    ) -> dict[str, Any]: ...


class VectorSearchRetriever:
    """Retriever backed by the Databricks Vector Search Delta Sync index."""

    def __init__(self, settings: Settings, index: SearchIndex | None = None) -> None:
        if index is None:
            from databricks.vector_search.client import VectorSearchClient

            client = VectorSearchClient(disable_notice=True)
            index = client.get_index(
                endpoint_name=settings.vs_endpoint, index_name=settings.vs_index
            )
        self._index = index

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        """Top-k chunks for the query, most similar first."""
        response = self._index.similarity_search(
            columns=RETRIEVE_COLUMNS, query_text=query, num_results=k
        )
        chunks = parse_search_response(response)
        logger.debug("retrieved %d chunks", len(chunks))
        return chunks


def parse_search_response(response: dict[str, Any]) -> list[RetrievedChunk]:
    """Turn a similarity_search response into RetrievedChunks, keeping the result order.

    The response lists column names in manifest.columns and one value list per hit in
    result.data_array; the similarity score is the last column.
    """
    names = [c["name"] for c in response.get("manifest", {}).get("columns", [])]
    rows = response.get("result", {}).get("data_array") or []
    chunks = []
    for values in rows:
        row = dict(zip(names, values, strict=True))
        page = row.get("page")
        chunks.append(
            RetrievedChunk(
                chunk_id=str(row["chunk_id"]),
                doc_id=str(row["doc_id"]),
                text=str(row["text"]),
                source_path=str(row["source_path"]),
                page=None if page is None else int(page),
                score=float(row.get("score", values[-1])),
            )
        )
    return chunks
