from types import SimpleNamespace
from typing import Any

import pytest
from databricks.sdk.service.serving import ChatMessageRole

from doc_analyzer.config import Settings
from doc_analyzer.rag.llm import ServingEndpointLLM


class FakeServingEndpoints:
    def __init__(self, content: str | None) -> None:
        self.content = content
        self.calls: list[dict[str, Any]] = []

    def query(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _llm(content: str | None) -> tuple[ServingEndpointLLM, FakeServingEndpoints]:
    endpoints = FakeServingEndpoints(content)
    client: Any = SimpleNamespace(serving_endpoints=endpoints)
    return ServingEndpointLLM(Settings(catalog="c", llm_endpoint="chat"), client=client), endpoints


def test_generate_sends_system_then_messages() -> None:
    llm, endpoints = _llm("30 days [handbook.pdf p.4].")

    text = llm.generate("Be grounded.", [{"role": "user", "content": "Question?"}])

    assert text == "30 days [handbook.pdf p.4]."
    call = endpoints.calls[0]
    assert call["name"] == "chat"
    assert [(m.role, m.content) for m in call["messages"]] == [
        (ChatMessageRole.SYSTEM, "Be grounded."),
        (ChatMessageRole.USER, "Question?"),
    ]


def test_generate_returns_empty_string_for_empty_content() -> None:
    llm, _ = _llm(None)
    assert llm.generate("s", [{"role": "user", "content": "q"}]) == ""


def test_missing_endpoint_raises() -> None:
    with pytest.raises(ValueError):
        ServingEndpointLLM(Settings(catalog="c"), client=SimpleNamespace())  # type: ignore[arg-type]
