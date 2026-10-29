# CLAUDE.md

This file gives Claude Code guidance for working in this repository.

## Project overview

**AI Document Analyzer**: a cloud-native Retrieval-Augmented Generation (RAG) platform on Azure + Databricks.
Users upload documents (PDF, DOCX, TXT, MD, HTML). The documents are ingested from Azure Data Lake Storage (ADLS Gen2), parsed, chunked and embedded with Spark, and stored in Delta Lake. A Databricks Vector Search index is built over the chunks. Questions are answered by an LLM, and every answer is grounded in the retrieved chunks and cites its sources.

**Stack:** Python 3.11, PySpark, Delta Lake, Databricks (Unity Catalog, Auto Loader, Workflows, Vector Search, Model Serving / Foundation Model APIs, MLflow), Azure Data Lake Storage Gen2, Databricks Asset Bundles (DABs) for deployment.

## Architecture

```
ADLS Gen2 (landing container: raw uploads)
   │  Auto Loader (cloudFiles, binaryFile format)
   ▼
bronze.documents_raw        – one row per file: path, bytes, size, modification_time, ingest_ts
   │  parse (PDF/DOCX/HTML → text), detect type, compute doc_id = sha256(content)
   ▼
silver.documents_parsed     – doc_id, source_path, title, text, page_map, mime_type, parse_status
   │  chunk (token-aware, overlap), keep page/section metadata
   ▼
gold.document_chunks        – chunk_id, doc_id, chunk_index, text, page, source_path, token_count
   │  (Change Data Feed ON)
   ▼
Databricks Vector Search    – Delta Sync index on gold.document_chunks
                              (managed embeddings via embedding endpoint, primary key = chunk_id)
   ▼
RAG service                 – retrieve top-k → build grounded prompt → LLM endpoint → answer + citations
                              packaged as an MLflow pyfunc model, deployed to Model Serving
```

Key design rules:
- **Medallion layers are idempotent.** Re-running a stage must not duplicate rows. Use `MERGE` on natural keys (`doc_id`, `chunk_id`), never blind `append` past bronze.
- **`doc_id` is content-addressed** (`sha256` of file bytes), so re-uploading the same file does not create duplicates. `chunk_id = f"{doc_id}:{chunk_index}"`.
- **Deletes propagate.** When a source file is removed, its silver/gold rows are deleted and the Delta Sync index picks up the change through CDF.
- **Grounding is mandatory.** The LLM prompt tells the model to answer only from the provided context, to cite `[source_path p.N]`, and to say it doesn't know when the context is insufficient. Never call the LLM without retrieved context.

## Repository layout (target)

```
databricks.yml                 # Asset Bundle: targets dev / staging / prod
resources/
  ingest_job.yml               # Workflow: bronze → silver → gold → index sync
  vector_search.yml            # endpoint + index definitions
  serving.yml                  # model serving endpoint for the RAG model
src/doc_analyzer/
  config.py                    # Settings dataclass; reads catalog/schema/endpoint names from env / job params
  ingest/
    autoloader.py              # ADLS → bronze (readStream cloudFiles)
    parse.py                   # bytes → text (pypdf, python-docx, BeautifulSoup); pure functions
    chunk.py                   # text → chunks; pure functions, no Spark dependency
    pipeline.py                # Spark jobs wiring parse/chunk into silver/gold with MERGE
  index/
    vector_search.py           # create/sync Delta Sync index via databricks-vectorsearch
  rag/
    retriever.py               # similarity_search wrapper → list[RetrievedChunk]
    prompt.py                  # grounded prompt template + citation formatting
    llm.py                     # LLM client (Databricks serving endpoint)
    chain.py                   # retrieve → prompt → generate; returns Answer(text, citations)
    model.py                   # MLflow pyfunc wrapper for Model Serving
  api/                         # optional FastAPI / Databricks App front end for upload + Q&A
notebooks/                     # thin notebooks that call into src/ (no business logic in notebooks)
tests/
  unit/                        # pure-Python tests (parse, chunk, prompt, chain with fakes)
  integration/                 # local Spark + delta-spark tests for pipeline MERGE logic
pyproject.toml
```

## Configuration

All environment-specific names come from `config.py`, never hard-coded:

| Setting | Example (dev) |
|---|---|
| `CATALOG` | `doc_analyzer_dev` |
| `SCHEMA_BRONZE` / `SILVER` / `GOLD` | `bronze` / `silver` / `gold` |
| `LANDING_PATH` | `abfss://landing@<storageaccount>.dfs.core.windows.net/uploads/` |
| `CHECKPOINT_PATH` | Unity Catalog volume, e.g. `/Volumes/doc_analyzer_dev/ops/checkpoints/` |
| `VS_ENDPOINT` | `doc-analyzer-vs` |
| `VS_INDEX` | `doc_analyzer_dev.gold.document_chunks_index` |
| `EMBEDDING_ENDPOINT` | `databricks-bge-large-en` (or another embedding endpoint) |
| `LLM_ENDPOINT` | the chat model serving endpoint name |
| `TOP_K` / `CHUNK_TOKENS` / `CHUNK_OVERLAP` | `5` / `512` / `64` |

- ADLS access goes through a **Unity Catalog external location + storage credential** (managed identity). Do not put storage keys, SAS tokens or service-principal secrets in code or notebooks. If a secret is unavoidable, read it with `dbutils.secrets.get(scope, key)`.
- Never commit `.databrickscfg`, `.env` or tokens.

## Common commands

```bash
# setup
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# quality
ruff check . && ruff format --check .
mypy src
pytest tests/unit                      # fast, no Spark
pytest tests/integration               # needs Java 11/17 for local Spark + delta-spark

# deploy / run (Databricks CLI ≥ 0.218)
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run ingest_job -t dev
```

## Coding conventions

- Keep **parsing, chunking, prompt building and the chain logic pure Python** with no Spark or Databricks imports, so they can be unit tested locally. Spark code goes in `pipeline.py` / `autoloader.py` and calls these functions through `pandas_udf` or `mapInPandas`.
- Prefer `mapInPandas` / `pandas_udf` over row-at-a-time Python UDFs for parsing and chunking.
- Define explicit `StructType` schemas for every table. Don't rely on schema inference past bronze.
- Create Delta tables with `delta.enableChangeDataFeed = true` on gold (required for Delta Sync).
- Streaming jobs use `trigger(availableNow=True)` in scheduled workflows, with one checkpoint per stream.
- A parse failure must not fail the batch. Record `parse_status = 'error'` and `parse_error` in silver and continue.
- Type hints everywhere. Use dataclasses for `RetrievedChunk`, `Answer` and `Citation`.
- Notebooks stay thin: import from `doc_analyzer`, read widgets/params, call one function.
- Use the `logging` module (no `print`) in `src/`.

## Testing guidance

- Unit test `chunk.py` for boundary cases: empty text, text shorter than one chunk, overlap correctness, preservation of page metadata.
- Test `chain.py` with a fake retriever and a fake LLM. Assert that the context is in the prompt, that citations map back to `chunk_id`s, and that an empty retrieval returns a "not found in the documents" answer instead of calling the LLM.
- Integration tests run the pipeline twice on the same input and assert that row counts are unchanged (idempotency).
- Evaluate RAG quality with `mlflow.evaluate` on a small golden Q&A set in `tests/eval/` before changing prompts, chunk size or the model.

## When making changes

- If you change a table schema, update its `StructType`, add a migration note, and check that the vector index columns still match.
- If you change chunking parameters, the gold table and the index must be rebuilt. Call this out in the PR.
- If you change the prompt or the model, re-run the eval set and report the metrics.
- Run `ruff`, `mypy` and `pytest tests/unit` before you consider a task done.
