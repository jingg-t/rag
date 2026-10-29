"""retrieve → build grounded prompt → generate → answer with citations."""

from __future__ import annotations

from doc_analyzer.rag.llm import LLMClient
from doc_analyzer.rag.retriever import Retriever
from doc_analyzer.rag.types import Answer

NOT_FOUND_ANSWER = "I couldn't find this in the uploaded documents."


class RAGChain:
    def __init__(self, retriever: Retriever, llm: LLMClient, top_k: int = 5) -> None:
        # TODO: implement
        raise NotImplementedError

    def answer(self, question: str) -> Answer:
        """Answer the question from retrieved chunks. Returns NOT_FOUND_ANSWER without calling
        the LLM when nothing is retrieved."""
        # TODO: implement
        raise NotImplementedError
