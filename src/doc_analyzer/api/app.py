"""Optional front end: upload documents to ADLS and ask questions via the serving endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI, UploadFile

    from doc_analyzer.config import Settings


def create_app(settings: Settings) -> FastAPI:
    """FastAPI app with POST /documents and POST /ask."""
    # TODO: implement
    raise NotImplementedError


async def upload_document(file: UploadFile) -> dict[str, Any]:
    """Write the uploaded file to the ADLS landing path."""
    # TODO: implement
    raise NotImplementedError


async def ask(question: str) -> dict[str, Any]:
    """Query the RAG serving endpoint and return the answer with citations."""
    # TODO: implement
    raise NotImplementedError
