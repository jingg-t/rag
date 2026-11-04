from typing import Any

import pandas as pd
import pytest

from doc_analyzer.rag.chain import RAGChain
from doc_analyzer.rag.model import RAGModel, settings_from_config
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
