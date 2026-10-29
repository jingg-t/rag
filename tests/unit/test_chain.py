import pytest

# TODO: implement tests with a fake Retriever and fake LLMClient, then remove the skip marker
pytestmark = pytest.mark.skip(reason="not implemented")


def test_answer_includes_retrieved_context_in_prompt() -> None: ...


def test_answer_citations_map_to_chunk_ids() -> None: ...


def test_empty_retrieval_returns_not_found_without_calling_llm() -> None: ...
