"""MLflow pyfunc wrapper so the RAG chain can be deployed to Model Serving."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import mlflow.pyfunc

if TYPE_CHECKING:
    import pandas as pd

    from doc_analyzer.config import Settings


class RAGModel(mlflow.pyfunc.PythonModel):  # type: ignore[misc]
    def load_context(self, context: mlflow.pyfunc.PythonModelContext) -> None:
        """Build Settings and the RAGChain from the model's config."""
        # TODO: implement
        raise NotImplementedError

    def predict(
        self,
        context: mlflow.pyfunc.PythonModelContext,
        model_input: pd.DataFrame,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """One answer (text + citations) per input question."""
        # TODO: implement
        raise NotImplementedError


def log_model(settings: Settings, registered_model_name: str) -> str:
    """Log and register RAGModel in Unity Catalog; return the model URI."""
    # TODO: implement
    raise NotImplementedError
