from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from doc_analyzer.rag.chain import RAGChain
from doc_analyzer.rag.model import RAGModel, deploy_endpoint, settings_from_config
from doc_analyzer.rag.types import RetrievedChunk

CHUNK = RetrievedChunk("d1:3", "d1", "Refunds take 30 days.", "handbook.pdf", 4, 0.9)


class FakeRetriever:
    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        return [CHUNK]


class FakeLLM:
    def generate(self, system: str, messages: list[dict[str, Any]]) -> str:
        return "Refunds take 30 days [handbook.pdf p.4]."


def _model() -> RAGModel:
    model = RAGModel(chain=RAGChain(FakeRetriever(), FakeLLM()))
    model.load_context(None)  # type: ignore[arg-type]
    return model


def test_predict_returns_answer_and_citations_per_question() -> None:
    questions = pd.DataFrame({"question": ["How long do refunds take?", "Refund time?"]})

    result = _model().predict(None, questions)  # type: ignore[arg-type]

    assert len(result) == 2
    assert result[0] == {
        "answer": "Refunds take 30 days [handbook.pdf p.4].",
        "citations": [{"chunk_id": "d1:3", "source_path": "handbook.pdf", "page": 4}],
    }


def test_predict_requires_question_column() -> None:
    with pytest.raises(ValueError):
        _model().predict(None, pd.DataFrame({"query": ["x"]}))  # type: ignore[arg-type]


def test_settings_from_config_ignores_unknown_keys() -> None:
    settings = settings_from_config({"catalog": "c", "top_k": 3, "unknown": "x"})
    assert settings.catalog == "c"
    assert settings.top_k == 3


def test_deploy_endpoint_creates_missing_endpoint() -> None:
    client = MagicMock()
    client.serving_endpoints.list.return_value = []

    deploy_endpoint("rag", "cat.gold.rag_model", "3", client=client)

    client.serving_endpoints.update_config.assert_not_called()
    kwargs = client.serving_endpoints.create.call_args.kwargs
    assert kwargs["name"] == "rag"
    entity = kwargs["config"].served_entities[0]
    assert (entity.entity_name, entity.entity_version) == ("cat.gold.rag_model", "3")


def test_deploy_endpoint_updates_existing_endpoint() -> None:
    client = MagicMock()
    client.serving_endpoints.list.return_value = [SimpleNamespace(name="rag")]

    deploy_endpoint("rag", "cat.gold.rag_model", "4", client=client)

    client.serving_endpoints.create.assert_not_called()
    kwargs = client.serving_endpoints.update_config.call_args.kwargs
    assert kwargs["name"] == "rag"
    assert kwargs["served_entities"][0].entity_version == "4"
