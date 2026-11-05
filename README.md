# AI Document Analyzer

A cloud-native Retrieval-Augmented Generation (RAG) platform on Azure and Databricks. Upload documents and ask questions about them. Answers come only from the retrieved passages and cite their sources, such as `[handbook.pdf p.4]`.

**Stack:** Python, PySpark, Delta Lake, Azure Data Lake Storage Gen2, Databricks (Unity Catalog, Auto Loader, Workflows, Vector Search, Model Serving, MLflow), Databricks Asset Bundles.

## How it works

```
ADLS Gen2 landing container (PDF, DOCX, TXT, MD, HTML)
   │  Auto Loader (binaryFile)
   ▼
bronze.documents_raw      one row per ingested file: path, bytes, size, modification time
   │  parse to text, doc_id = sha256(content)
   ▼
silver.documents_parsed   text, page map, MIME type, parse status
   │  token-aware chunking with overlap
   ▼
gold.document_chunks      chunk text, page, source path, token count (Change Data Feed on)
   │  Delta Sync with managed embeddings
   ▼
Databricks Vector Search
   │  top-k retrieval
   ▼
RAG chain                 grounded prompt → LLM endpoint → answer + citations
                          packaged as an MLflow model on Model Serving
```
## Repository layout

```
databricks.yml         Asset Bundle: variables and dev / staging / prod targets
resources/             Job definitions for ingestion and model deployment
notebooks/             Thin job entry points that call into src/
src/doc_analyzer/
  config.py            Settings from environment variables and job parameters
  ingest/              Auto Loader, parsing, chunking, table schemas, Spark pipeline
  index/               Vector Search endpoint and index management
  rag/                 Retriever, prompt, LLM client, chain, MLflow model
  api/                 Optional front end (stub)
tests/
  unit/                Pure Python tests
  integration/         Local Spark and Delta tests
```

## Local development

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

ruff check . && ruff format --check .
mypy src
pytest tests/unit
pytest tests/integration
```

On Windows, local Spark also needs `winutils.exe` and `hadoop.dll`. Put them in `C:\hadoop\bin`, set `HADOOP_HOME=C:\hadoop` and add `C:\hadoop\bin` to `PATH`. Without them, the integration tests are skipped.

The first run downloads the tokenizer from Hugging Face.

## Deployment

### Prerequisites

- An Azure subscription with:
  - An ADLS Gen2 storage account (hierarchical namespace on) with `landing` and `catalog` containers
  - A Premium Azure Databricks workspace with Unity Catalog
  - A Databricks access connector with **Storage Blob Data Contributor** on the storage account
- Databricks CLI 0.218 or later, logged in with `databricks auth login --host <workspace-url>`

### Unity Catalog objects

Create these once per environment:

| Object | Example for `dev` |
|---|---|
| Storage credential | `doc_analyzer_cred`, using the access connector's managed identity |
| External locations | `landing` and `catalog_storage`, one per container |
| Catalog | `doc_analyzer_dev`, with the `catalog` container as its managed location |
| Schema | `doc_analyzer_dev.ops` |
| Volumes | `ops.checkpoints` and `ops.models` |

The jobs create the bronze, silver and gold schemas and tables themselves.

## Configuration

Settings come from environment variables or job parameters, and job parameters take priority. See [config.py](src/doc_analyzer/config.py).

| Setting | Purpose | Default |
|---|---|---|
| `CATALOG` | Unity Catalog catalog | Required |
| `LANDING_PATH` | `abfss://` path of the uploads | None |
| `CHECKPOINT_PATH` | Auto Loader checkpoint location | None |
| `VS_ENDPOINT` | Vector Search endpoint | `doc-analyzer-vs` |
| `VS_INDEX` | Three-part index name | None |
| `EMBEDDING_ENDPOINT` | Embedding model endpoint | `databricks-gte-large-en` |
| `LLM_ENDPOINT` | Chat model endpoint | None |
| `TOP_K` | Chunks retrieved per question | `5` |
| `CHUNK_TOKENS` | Maximum tokens per chunk | `512` |
| `CHUNK_OVERLAP` | Tokens shared by consecutive chunks | `64` |

The `dev` target in `databricks.yml` overrides the embedding endpoint with `databricks-bge-large-en`.

Storage access goes through the Unity Catalog external location and the managed identity, so no storage keys or tokens are needed in code. Never commit `.databrickscfg`, `.env` or tokens.

## Limitations

- **No OCR:** scanned PDFs with no text layer can't yield any searchable text.
- **Manual ingest in `dev`:** development mode pauses the file-arrival trigger, so run `ingest_job` after uploading.
- **Changing chunk settings:** existing documents aren't re-chunked automatically. Truncate the gold table and re-run the job to rebuild it and the index.
