from typing import Any

from doc_analyzer.rag.chain import NOT_FOUND_ANSWER, RAGChain
from doc_analyzer.rag.prompt import SYSTEM_PROMPT
from doc_analyzer.rag.types import RetrievedChunk

HANDBOOK = RetrievedChunk(
    chunk_id="d1:3",
    doc_id="d1",
    text="Refunds are processed within 30 days.",
    source_path="handbook.pdf",
    page=4,
    score=0.92,
)
FAQ = RetrievedChunk(
    chunk_id="d2:0",
    doc_id="d2",
    text="Support is available on weekdays.",
    source_path="faq.html",
    page=1,
    score=0.81,
)


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        self.calls.append((query, k))
        return self.chunks[:k]


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, list[dict[str, Any]]]] = []

    def generate(self, system: str, messages: list[dict[str, Any]]) -> str:
        self.calls.append((system, messages))
        return self.response


def _prompt_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(str(m["content"]) for m in messages)


def test_answer_retrieves_top_k_for_question() -> None:
    retriever = FakeRetriever([HANDBOOK, FAQ])
    chain = RAGChain(retriever, FakeLLM("ok"), top_k=3)

    chain.answer("How long do refunds take?")

    assert retriever.calls == [("How long do refunds take?", 3)]


def test_answer_includes_retrieved_context_in_prompt() -> None:
    llm = FakeLLM("30 days [handbook.pdf p.4].")
    chain = RAGChain(FakeRetriever([HANDBOOK, FAQ]), llm)

    chain.answer("How long do refunds take?")

    assert len(llm.calls) == 1
    system, messages = llm.calls[0]
    assert system == SYSTEM_PROMPT
    prompt = _prompt_text(messages)
    assert HANDBOOK.text in prompt
    assert FAQ.text in prompt
    assert "How long do refunds take?" in prompt


def test_answer_citations_map_to_chunk_ids() -> None:
    llm = FakeLLM("Refunds take 30 days [handbook.pdf p.4].")
    chain = RAGChain(FakeRetriever([HANDBOOK, FAQ]), llm)

    answer = chain.answer("How long do refunds take?")

    assert answer.text == "Refunds take 30 days [handbook.pdf p.4]."
    assert [c.chunk_id for c in answer.citations] == ["d1:3"]
    assert answer.retrieved == [HANDBOOK, FAQ]


def test_answer_without_citations_has_empty_citations() -> None:
    chain = RAGChain(FakeRetriever([HANDBOOK]), FakeLLM("The context doesn't say."))
    assert chain.answer("What is the CEO's name?").citations == []


def test_empty_retrieval_returns_not_found_without_calling_llm() -> None:
    llm = FakeLLM("should not be called")
    chain = RAGChain(FakeRetriever([]), llm)

    answer = chain.answer("What is the meaning of life?")

    assert answer.text == NOT_FOUND_ANSWER
    assert answer.citations == []
    assert answer.retrieved == []
    assert llm.calls == []
