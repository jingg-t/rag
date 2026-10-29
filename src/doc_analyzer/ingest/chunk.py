"""Text → chunks. Pure functions, no Spark imports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from doc_analyzer.ingest.parse import Page


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    text: str
    page: int | None
    token_count: int


def count_tokens(text: str) -> int:
    """Token count used for chunk sizing (should match the embedding model's tokenizer)."""
    # TODO: implement
    raise NotImplementedError


def chunk_pages(
    pages: Sequence[Page],
    chunk_tokens: int,
    overlap: int,
) -> list[Chunk]:
    """Split pages into overlapping, token-bounded chunks, keeping the page each chunk starts on."""
    # TODO: implement
    raise NotImplementedError


def make_chunk_id(doc_id: str, chunk_index: int) -> str:
    """Stable chunk primary key: '{doc_id}:{chunk_index}'."""
    # TODO: implement
    raise NotImplementedError
