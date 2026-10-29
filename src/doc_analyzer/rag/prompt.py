"""Grounded prompt template and citation formatting."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from doc_analyzer.rag.types import Citation, RetrievedChunk

# TODO: answer only from context, cite [source_path p.N], say when the context is insufficient.
SYSTEM_PROMPT = ""


def format_citation(chunk: RetrievedChunk) -> str:
    """Citation label for a chunk, e.g. '[handbook.pdf p.4]'."""
    # TODO: implement
    raise NotImplementedError


def format_context(chunks: Sequence[RetrievedChunk]) -> str:
    """Render retrieved chunks as a numbered context block with their citation labels."""
    # TODO: implement
    raise NotImplementedError


def build_messages(question: str, chunks: Sequence[RetrievedChunk]) -> list[dict[str, Any]]:
    """Chat messages for the LLM: context first, then the question."""
    # TODO: implement
    raise NotImplementedError


def extract_citations(answer_text: str, chunks: Sequence[RetrievedChunk]) -> list[Citation]:
    """Map citation labels found in the answer back to the retrieved chunks."""
    # TODO: implement
    raise NotImplementedError
