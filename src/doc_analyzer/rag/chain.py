"""retrieve → build grounded prompt → generate → answer with citations."""

from __future__ import annotations

import logging

from doc_analyzer.rag.llm import LLMClient
from doc_analyzer.rag.prompt import SYSTEM_PROMPT, build_messages, extract_citations
from doc_analyzer.rag.retriever import Retriever
from doc_analyzer.rag.types import Answer

logger = logging.getLogger(__name__)

NOT_FOUND_ANSWER = "I couldn't find this in the uploaded documents."


class RAGChain:
    def __init__(self, retriever: Retriever, llm: LLMClient, top_k: int = 5) -> None:
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        self._retriever = retriever
        self._llm = llm
        self._top_k = top_k

    def answer(self, question: str) -> Answer:
        """Answer the question from retrieved chunks. Returns NOT_FOUND_ANSWER without calling
        the LLM when nothing is retrieved."""
        chunks = self._retriever.retrieve(question, self._top_k)
        if not chunks:
            logger.info("no chunks retrieved; returning not-found answer")
            return Answer(text=NOT_FOUND_ANSWER)

        text = self._llm.generate(SYSTEM_PROMPT, build_messages(question, chunks))
        citations = extract_citations(text, chunks)
        logger.info("answered from %d chunks with %d citations", len(chunks), len(citations))
        return Answer(text=text, citations=citations, retrieved=list(chunks))
