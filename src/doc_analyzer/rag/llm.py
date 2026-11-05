"""LLM client for answer generation via a Databricks Model Serving endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

    from doc_analyzer.config import Settings

DEFAULT_MAX_TOKENS = 1024


class LLMClient(Protocol):
    def generate(self, system: str, messages: list[dict[str, Any]]) -> str: ...


class ServingEndpointLLM:
    """Calls the chat model behind settings.llm_endpoint."""

    def __init__(
        self,
        settings: Settings,
        client: WorkspaceClient | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        if not settings.llm_endpoint:
            raise ValueError("LLM_ENDPOINT is not set")
        if client is None:
            from databricks.sdk import WorkspaceClient

            client = WorkspaceClient()
        self._client = client
        self._endpoint = settings.llm_endpoint
        self._max_tokens = max_tokens

    def generate(self, system: str, messages: list[dict[str, Any]]) -> str:
        """Return the model's text response."""
        chat = [ChatMessage(role=ChatMessageRole.SYSTEM, content=system)]
        chat += [
            ChatMessage(role=ChatMessageRole(m["role"]), content=m["content"]) for m in messages
        ]
        response = self._client.serving_endpoints.query(
            name=self._endpoint, messages=chat, max_tokens=self._max_tokens
        )
        if not response.choices or response.choices[0].message is None:
            raise RuntimeError(f"endpoint {self._endpoint} returned no message")
        return response.choices[0].message.content or ""
