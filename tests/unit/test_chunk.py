import pytest

from doc_analyzer.ingest.chunk import chunk_pages, count_tokens, make_chunk_id
from doc_analyzer.ingest.parse import Page

CHUNK_TOKENS = 32
OVERLAP = 8


def _long_text(n: int = 200) -> str:
    # Numbered sentences, so every chunk's text is unique within the document.
    return " ".join(f"Sentence number {i}." for i in range(n))


def _spans(text: str, chunk_texts: list[str]) -> list[tuple[int, int]]:
    """(start, end) character offsets of each chunk in the original text, in order."""
    spans: list[tuple[int, int]] = []
    pos = 0
    for chunk_text in chunk_texts:
        start = text.find(chunk_text, pos)
        assert start != -1, f"chunk text is not a slice of the source: {chunk_text!r}"
        spans.append((start, start + len(chunk_text)))
        pos = start + 1
    return spans


def test_count_tokens_empty_is_zero() -> None:
    assert count_tokens("") == 0


def test_count_tokens_grows_with_text() -> None:
    assert 0 < count_tokens("hello") < count_tokens("hello world, this is longer")


@pytest.mark.parametrize("pages", [[], [Page(1, "")], [Page(1, "  \n "), Page(2, "")]])
def test_empty_text_yields_no_chunks(pages: list[Page]) -> None:
    assert chunk_pages(pages, CHUNK_TOKENS, OVERLAP) == []


def test_short_text_yields_single_chunk() -> None:
    text = "Refunds are processed within 30 days."

    chunks = chunk_pages([Page(1, text)], CHUNK_TOKENS, OVERLAP)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_index == 0
    assert chunk.text == text
    assert chunk.page == 1
    assert chunk.token_count == count_tokens(text)


def test_chunks_respect_token_limit() -> None:
    chunks = chunk_pages([Page(1, _long_text())], CHUNK_TOKENS, OVERLAP)

    assert len(chunks) > 1
    for chunk in chunks:
        assert 0 < chunk.token_count <= CHUNK_TOKENS
        assert count_tokens(chunk.text) <= CHUNK_TOKENS


def test_chunk_indexes_are_sequential() -> None:
    chunks = chunk_pages([Page(1, _long_text())], CHUNK_TOKENS, OVERLAP)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_text_is_original_text() -> None:
    # Chunks are slices of the source, not detokenized text (bge lowercases and splits words).
    text = "The Quick Brown Fox. " * 40
    for chunk in chunk_pages([Page(1, text)], CHUNK_TOKENS, OVERLAP):
        assert chunk.text in text


def test_consecutive_chunks_overlap() -> None:
    text = _long_text()
    chunks = chunk_pages([Page(1, text)], CHUNK_TOKENS, OVERLAP)
    spans = _spans(text, [c.text for c in chunks])

    for (prev_start, prev_end), (start, _) in zip(spans, spans[1:], strict=False):
        assert prev_start < start < prev_end  # next chunk starts inside the previous one
        assert count_tokens(text[start:prev_end]) > 0


def test_chunks_cover_whole_text() -> None:
    text = _long_text()
    spans = _spans(text, [c.text for c in chunk_pages([Page(1, text)], CHUNK_TOKENS, OVERLAP)])

    assert spans[0][0] == 0
    assert spans[-1][1] == len(text)


def test_zero_overlap_has_no_shared_text() -> None:
    text = _long_text()
    spans = _spans(text, [c.text for c in chunk_pages([Page(1, text)], CHUNK_TOKENS, 0)])

    for (_, prev_end), (start, _) in zip(spans, spans[1:], strict=False):
        assert start >= prev_end


def test_chunks_keep_page_metadata() -> None:
    pages = [
        Page(1, "Page one has a short introduction."),
        Page(2, _long_text(60)),
        Page(3, "Page three closes the document."),
    ]

    chunks = chunk_pages(pages, CHUNK_TOKENS, OVERLAP)

    assert chunks[0].page == 1
    assert chunks[-1].page in (2, 3)
    page_numbers = [c.page for c in chunks]
    assert page_numbers == sorted(page_numbers)  # never goes backwards
    assert 2 in page_numbers
    for chunk in chunks:
        if "Sentence number 30." in chunk.text:
            assert chunk.page == 2


def test_empty_page_does_not_shift_page_numbers() -> None:
    pages = [Page(1, ""), Page(2, "Only page two has text.")]

    chunks = chunk_pages(pages, CHUNK_TOKENS, OVERLAP)

    assert [c.page for c in chunks] == [2]


@pytest.mark.parametrize(("chunk_tokens", "overlap"), [(32, 32), (32, 40), (0, 0), (32, -1)])
def test_invalid_sizes_raise(chunk_tokens: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_pages([Page(1, "text")], chunk_tokens, overlap)


def test_make_chunk_id_format() -> None:
    assert make_chunk_id("abc123", 0) == "abc123:0"
    assert make_chunk_id("abc123", 17) == "abc123:17"
