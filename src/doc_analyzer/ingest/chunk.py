"""Text → chunks. Pure functions, no Spark imports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

from tokenizers import Tokenizer

from doc_analyzer.ingest.parse import Page

# Must match the embedding model, so chunk sizes are measured the way the model counts them.
# gte-large-en and bge-large-en share the same uncased WordPiece vocabulary.
TOKENIZER_NAME = "BAAI/bge-large-en-v1.5"


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    text: str
    page: int | None
    token_count: int


@dataclass(frozen=True)
class _Token:
    page_index: int  # index into the pages sequence
    word: int  # word id within the page, so words are never split between chunks
    start: int  # character offsets into the page text
    end: int


@lru_cache(maxsize=1)
def _tokenizer() -> Tokenizer:
    tokenizer = Tokenizer.from_pretrained(TOKENIZER_NAME)
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return tokenizer


def count_tokens(text: str) -> int:
    """Token count used for chunk sizing (should match the embedding model's tokenizer).

    Special tokens ([CLS], [SEP]) are not counted, so the empty string is 0 tokens.
    """
    if not text:
        return 0
    return len(_tokenizer().encode(text, add_special_tokens=False).ids)


def chunk_pages(
    pages: Sequence[Page],
    chunk_tokens: int,
    overlap: int,
) -> list[Chunk]:
    """Split pages into overlapping, token-bounded chunks, keeping the page each chunk starts on.

    Pages are treated as one token stream, so a chunk may run across a page break; its text
    then joins the page slices with a blank line. Chunk text is sliced from the original page
    text (not decoded from tokens), and boundaries are moved back to word starts so words are
    not cut in half, unless one word is longer than a whole chunk.

    Args:
        pages: Pages from parse; empty pages are skipped but keep their numbers.
        chunk_tokens: Maximum tokens per chunk.
        overlap: Tokens shared by consecutive chunks; must be less than chunk_tokens.

    Returns:
        Chunks numbered from 0. Empty list if there is no text.

    Raises:
        ValueError: If chunk_tokens <= 0, overlap < 0 or overlap >= chunk_tokens.
    """
    if chunk_tokens <= 0:
        raise ValueError(f"chunk_tokens must be positive, got {chunk_tokens}")
    if not 0 <= overlap < chunk_tokens:
        raise ValueError(f"overlap must be in [0, {chunk_tokens}), got {overlap}")

    tokens = _tokenize_pages(pages)
    chunks: list[Chunk] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_tokens, len(tokens))
        if end < len(tokens):
            end = _word_start(tokens, end, floor=start + 1)
        chunks.append(
            Chunk(
                chunk_index=len(chunks),
                text=_slice_text(pages, tokens[start:end]),
                page=pages[tokens[start].page_index].page_number,
                token_count=end - start,
            )
        )
        if end == len(tokens):
            break
        start = _word_start(tokens, end - overlap, floor=start + 1)
    return chunks


def make_chunk_id(doc_id: str, chunk_index: int) -> str:
    """Stable chunk primary key: '{doc_id}:{chunk_index}'."""
    return f"{doc_id}:{chunk_index}"


def _tokenize_pages(pages: Sequence[Page]) -> list[_Token]:
    tokenizer = _tokenizer()
    tokens: list[_Token] = []
    for page_index, page in enumerate(pages):
        if not page.text.strip():
            continue
        encoding = tokenizer.encode(page.text, add_special_tokens=False)
        for word, (start, end) in zip(encoding.word_ids, encoding.offsets, strict=True):
            tokens.append(_Token(page_index, -1 if word is None else word, start, end))
    return tokens


def _word_start(tokens: Sequence[_Token], i: int, floor: int) -> int:
    """Move index i back to the first token of its word, but not below floor."""
    j = i
    while j > floor and _same_word(tokens[j - 1], tokens[j]):
        j -= 1
    # A word longer than the whole window: cut inside it rather than stall.
    return j if j > floor or not _same_word(tokens[j - 1], tokens[j]) else i


def _same_word(a: _Token, b: _Token) -> bool:
    return a.page_index == b.page_index and a.word == b.word and a.word != -1


def _slice_text(pages: Sequence[Page], tokens: Sequence[_Token]) -> str:
    """Original text covered by the tokens, joining slices from different pages."""
    parts: list[str] = []
    first = tokens[0]
    for prev, token in zip(tokens, [*tokens[1:], None], strict=True):
        if token is None or token.page_index != prev.page_index:
            parts.append(pages[first.page_index].text[first.start : prev.end])
            first = token if token is not None else first
    return "\n\n".join(parts)
