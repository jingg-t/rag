"""LLM client for answer generation via a Databricks Model Serving endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from doc_analyzer.config import Settings


class LLMClient(Protocol):
    def generate(self, system: str, messages: list[dict[str, Any]]) -> str: ...


class ServingEndpointLLM:
    """Calls the chat model behind settings.llm_endpoint."""

    def __init__(self, settings: Settings) -> None:
        # TODO: implement
        raise NotImplementedError

    def generate(self, system: str, messages: list[dict[str, Any]]) -> str:
        """Return the model's text response."""
        # TODO: implement
        raise NotImplementedError
