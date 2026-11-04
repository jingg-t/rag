from doc_analyzer.rag.prompt import (
    SYSTEM_PROMPT,
    build_messages,
    extract_citations,
    format_citation,
    format_context,
)
from doc_analyzer.rag.types import Citation, RetrievedChunk


def _chunk(chunk_id: str, text: str, source_path: str, page: int | None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        doc_id=chunk_id.split(":")[0],
        text=text,
        source_path=source_path,
        page=page,
        score=0.9,
    )


HANDBOOK = _chunk("d1:3", "Refunds are processed within 30 days.", "handbook.pdf", 4)
FAQ = _chunk("d2:0", "Support is available on weekdays.", "faq.html", 1)


def test_system_prompt_requires_grounding() -> None:
    prompt = SYSTEM_PROMPT.lower()
    assert prompt.strip()
    assert "context" in prompt
    assert "cite" in prompt or "citation" in prompt


def test_format_citation_includes_source_and_page() -> None:
    assert format_citation(HANDBOOK) == "[handbook.pdf p.4]"


def test_format_citation_without_page() -> None:
    assert format_citation(_chunk("d3:0", "x", "notes.txt", None)) == "[notes.txt]"


def test_format_context_lists_every_chunk_with_label() -> None:
    context = format_context([HANDBOOK, FAQ])

    for chunk in (HANDBOOK, FAQ):
        assert chunk.text in context
        assert format_citation(chunk) in context
    assert context.index(HANDBOOK.text) < context.index(FAQ.text)  # keeps retrieval order


def test_build_messages_puts_context_before_question() -> None:
    question = "How long do refunds take?"

    messages = build_messages(question, [HANDBOOK, FAQ])

    assert messages[-1]["role"] == "user"
    assert all(m["role"] in ("user", "assistant") for m in messages)  # system is passed apart
    content = "\n".join(str(m["content"]) for m in messages)
    assert question in content
    assert content.index(HANDBOOK.text) < content.index(question)
    assert format_citation(HANDBOOK) in content


def test_extract_citations_maps_labels_to_chunks() -> None:
    answer = "Refunds take 30 days [handbook.pdf p.4]. Support works weekdays [faq.html p.1]."

    citations = extract_citations(answer, [HANDBOOK, FAQ])

    assert citations == [
        Citation(chunk_id="d1:3", source_path="handbook.pdf", page=4),
        Citation(chunk_id="d2:0", source_path="faq.html", page=1),
    ]


def test_extract_citations_ignores_unknown_labels() -> None:
    answer = "Refunds take 30 days [handbook.pdf p.4], see also [made-up.pdf p.9]."

    citations = extract_citations(answer, [HANDBOOK, FAQ])

    assert [c.chunk_id for c in citations] == ["d1:3"]


def test_extract_citations_deduplicates() -> None:
    answer = "30 days [handbook.pdf p.4]. Really, 30 days [handbook.pdf p.4]."
    assert len(extract_citations(answer, [HANDBOOK])) == 1


def test_extract_citations_without_labels_is_empty() -> None:
    assert extract_citations("I don't know.", [HANDBOOK]) == []
