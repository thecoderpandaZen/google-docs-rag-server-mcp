# Google Drive RAG Server with MCP Tooling

A production-ready Retrieval-Augmented Generation (RAG) server for Google Drive & Google Docs, exposed via Model Context Protocol (MCP) tools.

## Features

- **Continuous Indexing**: Automatically indexes Google Drive content with incremental updates
- **Semantic Search**: Vector-based search using OpenAI embeddings and pgvector
- **MCP Integration**: Exposes knowledge through structured MCP tool calls
- **Citation-Friendly**: Every result includes document links and metadata
- **Production-Ready**: Comprehensive logging, metrics, and error handling

## Architecture

```
┌─────────────────┐
│   MCP Server    │  (Port 8002)
│   FastAPI/SSE   │
└────────┬────────┘
         │
         │ HTTP
         ▼
┌─────────────────┐
│ Retrieval API   │  (Port 8001)
│   FastAPI       │
└────────┬────────┘
         │
         │ SQL + pgvector
         ▼
┌─────────────────┐       ┌──────────────┐
│   PostgreSQL    │◄──────│   Indexer    │
│   + pgvector    │       │   (Prefect)  │
└─────────────────┘       └──────┬───────┘
                                  │
                                  │ Google APIs
                                  ▼
                          ┌──────────────┐
                          │ Google Drive │
                          └──────────────┘
```

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Google Cloud Project with Drive API enabled
- Service Account with domain-wide delegation (for org-wide access)
- OpenAI API key

## Quick Start

### 1. Environment Setup

```bash
cp .env.example .env
```

Edit `.env` and configure:

- `DATABASE_URL`: PostgreSQL connection string
- `GOOGLE_SERVICE_ACCOUNT_FILE`: Path to service account JSON
- `OPENAI_API_KEY`: Your OpenAI API key

### 2. Start Services

```bash
cd docker
docker-compose up -d
```

This starts:
- PostgreSQL with pgvector
- Retrieval API (port 8001)
- Indexer worker

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Configure Sources

Edit `sources.yaml` to add your Google Drive folders or shared drives.

### 5. Start Indexing

```python
from gdrive_rag.indexer.flows import full_crawl_flow
import asyncio

# Run full crawl for a source
asyncio.run(full_crawl_flow("your-source-id"))
```

## API Endpoints

### Retrieval API (Port 8001)

- `GET /health` - Health check
- `POST /api/v1/search` - Semantic search
- `GET /api/v1/documents/{file_id}` - Get document by ID
- `GET /api/v1/changes` - List recent changes
- `POST /api/v1/reindex` - Trigger reindex (admin)
- `GET /metrics` - Prometheus metrics

### MCP Server (Port 8002)

- `GET /mcp/tools` - List available tools
- `POST /mcp/call/{tool_name}` - Invoke tool

#### Available MCP Tools

1. **search_docs**
   - Search documents using semantic search
   - Input: `query` (string), `max_results` (int)

2. **get_document**
   - Retrieve document with all chunks
   - Input: `file_id` (string)

3. **list_recent_changes**
   - List recently indexed/changed documents
   - Input: `since` (ISO datetime)

4. **reindex_source**
   - Trigger source reindexing (admin)
   - Input: `source_id` (string), `full_reindex` (bool)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to service account JSON | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `CHUNK_TARGET_SIZE` | Target chunk size (chars) | 600 |
| `CHUNK_OVERLAP` | Chunk overlap (chars) | 100 |
| `API_PORT` | Retrieval API port | 8001 |
| `MCP_PORT` | MCP server port | 8002 |
| `LOG_LEVEL` | Logging level | INFO |

### Source Configuration

Sources are defined in `sources.yaml`:

```yaml
sources:
  - id: "engineering-docs"
    name: "Engineering Documentation"
    type: "folder"
    config:
      folder_id: "abc123..."
      mime_types:
        - "application/vnd.google-apps.document"
        - "application/pdf"
```

## Development

### Install Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/ -v
```

### Type Checking

```bash
mypy src/gdrive_rag --strict
```

### Linting

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Deployment

### Docker Build

```bash
docker build -f docker/Dockerfile.api -t gdrive-rag-api .
docker build -f docker/Dockerfile.indexer -t gdrive-rag-indexer .
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Monitoring

### Prometheus Metrics

Metrics are exposed at `/metrics`:

- `gdrive_rag_indexed_documents_total` - Total documents indexed
- `gdrive_rag_indexed_chunks_total` - Total chunks created
- `gdrive_rag_search_requests_total` - Search request count
- `gdrive_rag_search_latency_seconds` - Search latency histogram

### Structured Logging

All logs are JSON-formatted for easy parsing:

```json
{
  "event": "search_completed",
  "timestamp": "2024-12-29T12:00:00Z",
  "logger": "gdrive_rag.services.retrieval",
  "level": "info",
  "query": "...",
  "results_count": 10
}
```

## Security

- API key authentication for Retrieval API
- Bearer token authentication for MCP server
- No secrets in logs or error messages
- Audit logs for all MCP tool calls
- Source-level access control

## Troubleshooting

### Database Connection Issues

```bash
# Check database connectivity
docker-compose exec postgres psql -U postgres -d gdrive_rag -c "SELECT 1"

# Verify pgvector extension
docker-compose exec postgres psql -U postgres -d gdrive_rag -c "SELECT * FROM pg_extension WHERE extname='vector'"
```

### Indexing Failures

Check indexer logs:

```bash
docker-compose logs indexer -f
```

Common issues:
- Service account permissions
- Invalid folder/drive IDs
- API rate limits

### Search Performance

For better search performance:

1. Ensure HNSW index is created:
   ```sql
   SELECT indexname FROM pg_indexes WHERE tablename = 'chunks';
   ```

2. Check query performance:
   ```sql
   EXPLAIN ANALYZE SELECT ... FROM chunks ...
   ```

## License

MIT

## Support

For issues and questions, please open a GitHub issue.
