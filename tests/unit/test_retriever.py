from typing import Any

from doc_analyzer.config import Settings
from doc_analyzer.rag.retriever import (
    RETRIEVE_COLUMNS,
    VectorSearchRetriever,
    parse_search_response,
)
from doc_analyzer.rag.types import RetrievedChunk

RESPONSE: dict[str, Any] = {
    "manifest": {
        "columns": [{"name": c} for c in [*RETRIEVE_COLUMNS, "score"]],
    },
    "result": {
        "row_count": 2,
        "data_array": [
            ["d1:3", "d1", "Refunds take 30 days.", "handbook.pdf", 4.0, 0.92],
            ["d2:0", "d2", "Support on weekdays.", "faq.html", None, 0.81],
        ],
    },
}


class FakeIndex:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def similarity_search(
        self, columns: list[str], query_text: str, num_results: int
    ) -> dict[str, Any]:
        self.calls.append({"columns": columns, "query_text": query_text, "k": num_results})
        return self.response


def test_parse_search_response_keeps_order_and_types() -> None:
    assert parse_search_response(RESPONSE) == [
        RetrievedChunk("d1:3", "d1", "Refunds take 30 days.", "handbook.pdf", 4, 0.92),
        RetrievedChunk("d2:0", "d2", "Support on weekdays.", "faq.html", None, 0.81),
    ]


def test_parse_search_response_without_hits() -> None:
    empty = {"manifest": RESPONSE["manifest"], "result": {"row_count": 0}}
    assert parse_search_response(empty) == []


def test_retrieve_queries_index_with_k() -> None:
    index = FakeIndex(RESPONSE)
    retriever = VectorSearchRetriever(Settings(catalog="c"), index=index)

    chunks = retriever.retrieve("How long do refunds take?", k=7)

    assert index.calls == [
        {"columns": RETRIEVE_COLUMNS, "query_text": "How long do refunds take?", "k": 7}
    ]
    assert [c.chunk_id for c in chunks] == ["d1:3", "d2:0"]
