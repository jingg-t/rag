"""MLflow pyfunc wrapper so the RAG chain can be deployed to Model Serving."""

from __future__ import annotations

import dataclasses
import logging
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any

import mlflow
import pandas as pd
from mlflow.models import infer_signature
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksVectorSearchIndex
from mlflow.pyfunc.model import PythonModel, PythonModelContext

from doc_analyzer.config import Settings
from doc_analyzer.rag.chain import RAGChain
from doc_analyzer.rag.llm import ServingEndpointLLM
from doc_analyzer.rag.retriever import VectorSearchRetriever

if TYPE_CHECKING:
    from doc_analyzer.rag.types import Answer

logger = logging.getLogger(__name__)

QUESTION_COLUMN = "question"
_SERVING_PACKAGES = ["mlflow", "pandas", "databricks-sdk", "databricks-vectorsearch"]


class RAGModel(PythonModel):
    def __init__(self, chain: RAGChain | None = None) -> None:
        self._chain = chain

    def load_context(self, context: PythonModelContext) -> None:
        """Build Settings and the RAGChain from the model's config."""
        if self._chain is not None:
            return
        settings = settings_from_config(context.model_config or {})
        self._chain = RAGChain(
            VectorSearchRetriever(settings), ServingEndpointLLM(settings), top_k=settings.top_k
        )

    def predict(
        self,
        context: PythonModelContext,
        model_input: pd.DataFrame,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """One answer (text + citations) per input question."""
        if self._chain is None:
            raise RuntimeError("model not loaded: load_context was not called")
        if QUESTION_COLUMN not in model_input.columns:
            raise ValueError(f"input needs a '{QUESTION_COLUMN}' column")
        return [answer_to_dict(self._chain.answer(str(q))) for q in model_input[QUESTION_COLUMN]]


def answer_to_dict(answer: Answer) -> dict[str, Any]:
    """Serving response for one answer."""
    return {
        "answer": answer.text,
        "citations": [dataclasses.asdict(c) for c in answer.citations],
    }


def settings_from_config(config: dict[str, Any]) -> Settings:
    """Settings from the logged model_config, ignoring unknown keys."""
    names = {f.name for f in dataclasses.fields(Settings)}
    return Settings(**{k: v for k, v in config.items() if k in names})


def log_model(settings: Settings, registered_model_name: str) -> str:
    """Log and register RAGModel in Unity Catalog; return the model URI."""
    for name, value in [
        ("VS_ENDPOINT", settings.vs_endpoint),
        ("VS_INDEX", settings.vs_index),
        ("LLM_ENDPOINT", settings.llm_endpoint),
    ]:
        if not value:
            raise ValueError(f"{name} is not set")

    input_example = pd.DataFrame({QUESTION_COLUMN: ["How long do refunds take?"]})
    output_example = [
        {
            "answer": "Refunds take 30 days [handbook.pdf p.4].",
            "citations": [{"chunk_id": "abc:0", "source_path": "handbook.pdf", "page": 4}],
        }
    ]
    mlflow.set_registry_uri("databricks-uc")
    with mlflow.start_run(run_name="rag_model"):
        info = mlflow.pyfunc.log_model(
            name="rag_model",
            python_model=RAGModel(),
            model_config=dataclasses.asdict(settings),
            code_paths=[str(Path(__file__).resolve().parents[1])],  # the doc_analyzer package
            pip_requirements=[f"{p}=={version(p)}" for p in _SERVING_PACKAGES],
            # No input_example: MLflow would run predict on it, querying live endpoints.
            signature=infer_signature(input_example, output_example),
            resources=[
                DatabricksVectorSearchIndex(index_name=settings.vs_index),
                DatabricksServingEndpoint(endpoint_name=settings.llm_endpoint),
                DatabricksServingEndpoint(endpoint_name=settings.embedding_endpoint),
            ],
            registered_model_name=registered_model_name,
        )
    logger.info("logged %s as %s", info.model_uri, registered_model_name)
    return str(info.model_uri)
