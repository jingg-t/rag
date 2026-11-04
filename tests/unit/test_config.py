import pytest

from doc_analyzer.config import Settings


def test_table_names_are_fully_qualified() -> None:
    settings = Settings(catalog="doc_analyzer_dev")

    assert settings.bronze_table == "doc_analyzer_dev.bronze.documents_raw"
    assert settings.silver_table == "doc_analyzer_dev.silver.documents_parsed"
    assert settings.gold_table == "doc_analyzer_dev.gold.document_chunks"


def test_table_names_use_custom_schemas() -> None:
    settings = Settings(catalog="c", schema_bronze="b", schema_silver="s", schema_gold="g")

    assert settings.bronze_table == "c.b.documents_raw"
    assert settings.silver_table == "c.s.documents_parsed"
    assert settings.gold_table == "c.g.document_chunks"


def test_from_env_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CATALOG", "doc_analyzer_dev")
    monkeypatch.setenv("LLM_ENDPOINT", "claude-endpoint")
    monkeypatch.setenv("TOP_K", "8")
    monkeypatch.setenv("CHUNK_TOKENS", "256")

    settings = Settings.from_env()

    assert settings.catalog == "doc_analyzer_dev"
    assert settings.llm_endpoint == "claude-endpoint"
    assert settings.top_k == 8
    assert settings.chunk_tokens == 256
    assert settings.chunk_overlap == 64  # default kept


def test_from_env_overrides_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CATALOG", "doc_analyzer_dev")
    monkeypatch.setenv("TOP_K", "8")

    settings = Settings.from_env({"CATALOG": "doc_analyzer_prod", "TOP_K": "3"})

    assert settings.catalog == "doc_analyzer_prod"
    assert settings.top_k == 3


def test_from_env_requires_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CATALOG", raising=False)
    with pytest.raises((KeyError, ValueError)):
        Settings.from_env()
