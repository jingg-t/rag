"""Data types passed between retriever, prompt builder, LLM and chain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    text: str
    source_path: str
    page: int | None
    score: float


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    source_path: str
    page: int | None


@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    retrieved: list[RetrievedChunk] = field(default_factory=list)
