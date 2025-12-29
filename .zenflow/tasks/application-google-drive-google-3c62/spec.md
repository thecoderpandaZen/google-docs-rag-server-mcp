# Technical Specification: Google Drive RAG Server with MCP

**Version**: 1.0  
**Date**: 2024-12-29  
**Status**: Draft

---

## 1. Technical Context

### 1.1 Technology Stack

**Core Language & Runtime**:
- Python 3.11+ (CPython)
- Type hints throughout (mypy strict mode)
- asyncio-based concurrency model

**Web Framework**:
- FastAPI 0.110+ (async ASGI framework)
- Pydantic v2 for schema validation
- uvicorn ASGI server

**Database**:
- PostgreSQL 15+ with pgvector 0.5.0+ extension
- asyncpg for async database driver
- SQLAlchemy 2.0+ ORM with async support
- Alembic for schema migrations

**Vector Search**:
- pgvector with HNSW indexing (preferred over IVFFlat for accuracy)
- Dimension: 1536 (OpenAI text-embedding-3-small)

**Google APIs**:
- google-api-python-client 2.100+
- google-auth 2.23+
- Drive API v3
- Docs API v1

**Embedding Provider**:
- OpenAI Python SDK 1.10+ (primary)
- sentence-transformers 2.2+ (optional fallback)

**Workflow Orchestration**:
- Prefect 2.14+ (recommended)
- prefect-sqlalchemy for state persistence

**Testing & Quality**:
- pytest 7.4+
- pytest-asyncio for async tests
- httpx for async HTTP testing
- ruff for linting (replaces flake8, black, isort)
- mypy for type checking
- coverage.py for test coverage

**Containerization**:
- Docker with multi-stage builds
- Python 3.11-slim base image
- docker-compose for local development

**Observability**:
- structlog for structured logging
- prometheus-client for metrics
- OpenTelemetry (optional, future)

### 1.2 Dependency Rationale

**FastAPI over Flask/Django**:
- Native async support (critical for I/O-bound operations)
- Automatic OpenAPI documentation
- Pydantic integration for type-safe validation
- Best-in-class performance for API workloads

**asyncpg over psycopg2**:
- 3x faster for high-concurrency workloads
- Native async support matches FastAPI model
- Better connection pooling

**Prefect over Airflow**:
- Lighter operational footprint
- Python-native (no DAG files)
- Better local development experience
- Adequate for single-tenant indexing workflows

**HNSW over IVFFlat**:
- Better recall at same speed
- No training required
- More predictable performance

---

## 2. Implementation Approach

### 2.1 Architecture Overview

The system follows a **3-tier service-oriented architecture**:

```
┌─────────────────┐
│   MCP Server    │  (FastAPI app, SSE transport)
│   Port: 8000    │
└────────┬────────┘
         │
         │ HTTP
         ▼
┌─────────────────┐
│ Retrieval API   │  (FastAPI app, stateless)
│   Port: 8001    │
└────────┬────────┘
         │
         │ SQL
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

**Design Principles**:
1. **Separation of Concerns**: Each service has a single responsibility
2. **Stateless APIs**: All state in database, enabling horizontal scaling
3. **Idempotency**: All indexing operations are idempotent for safe retries
4. **Fail-Safe Defaults**: System degrades gracefully on partial failures

### 2.2 Project Structure

```
gdrive-rag/
├── src/
│   ├── gdrive_rag/
│   │   ├── __init__.py
│   │   ├── config.py              # Centralized configuration
│   │   ├── models/                # Database models
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── source.py
│   │   │   ├── document.py
│   │   │   └── chunk.py
│   │   ├── schemas/               # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── search.py
│   │   │   ├── document.py
│   │   │   └── mcp.py
│   │   ├── services/              # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── google_drive.py
│   │   │   ├── embedding.py
│   │   │   ├── chunking.py
│   │   │   └── retrieval.py
│   │   ├── indexer/               # Indexing workflows
│   │   │   ├── __init__.py
│   │   │   ├── flows.py           # Prefect flows
│   │   │   ├── tasks.py           # Prefect tasks
│   │   │   └── extractors/
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── gdoc.py
│   │   │       ├── pdf.py
│   │   │       └── docx.py
│   │   ├── api/                   # Retrieval API
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── deps.py            # Dependencies
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── search.py
│   │   │       ├── documents.py
│   │   │       ├── changes.py
│   │   │       └── admin.py
│   │   ├── mcp/                   # MCP Server
│   │   │   ├── __init__.py
│   │   │   ├── server.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── search_docs.py
│   │   │       ├── get_document.py
│   │   │       ├── list_changes.py
│   │   │       └── reindex_source.py
│   │   ├── db/                    # Database utilities
│   │   │   ├── __init__.py
│   │   │   ├── session.py
│   │   │   └── migrations/        # Alembic migrations
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logging.py
│   │       └── metrics.py
├── tests/
│   ├── unit/
│   │   ├── test_chunking.py
│   │   ├── test_embedding.py
│   │   └── test_extractors.py
│   ├── integration/
│   │   ├── test_indexer.py
│   │   ├── test_retrieval.py
│   │   └── test_mcp.py
│   └── conftest.py
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.indexer
│   └── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── mcp.json                       # MCP server manifest
├── sources.yaml                   # Indexing sources config
└── README.md
```

### 2.3 Module Responsibilities

**services/google_drive.py**:
- Google Drive API client wrapper
- Authentication with service account
- File enumeration with filtering
- Change tracking via Changes API
- Exponential backoff and retry logic

**services/embedding.py**:
- OpenAI embedding client
- Batch processing (up to 100 texts)
- Rate limiting and quotas
- Fallback to sentence-transformers (optional)

**services/chunking.py**:
- Structure-aware text chunking
- Markdown/HTML parsing for hierarchy
- Overlap management
- Metadata preservation (headings, section context)

**services/retrieval.py**:
- Vector similarity search with pgvector
- Hybrid search (vector + metadata filters)
- Result ranking and deduplication
- Citation formatting

**indexer/flows.py**:
- Prefect flow definitions
- Full crawl flow
- Incremental update flow
- Single document reindex flow

**indexer/tasks.py**:
- Prefect tasks (atomic, retriable units)
- Task: enumerate_files
- Task: extract_content
- Task: chunk_document
- Task: generate_embeddings
- Task: upsert_chunks

**api/routes/search.py**:
- POST /api/v1/search endpoint
- Request validation
- Query embedding generation
- Retrieval service invocation

**mcp/tools/search_docs.py**:
- MCP tool implementation
- Input schema validation
- Mapping to Retrieval API
- Error handling and logging

---

## 3. Data Model

### 3.1 Database Schema (SQLAlchemy Models)

**models/source.py**:
```python
class Source(Base):
    __tablename__ = "sources"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # folder, shared_drive, file_list
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    documents: Mapped[List["Document"]] = relationship(back_populates="source")
```

**models/document.py**:
```python
class Document(Base):
    __tablename__ = "documents"
    
    file_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    web_view_link: Mapped[str] = mapped_column(Text, nullable=False)
    modified_time: Mapped[datetime] = mapped_column(nullable=False)
    owners: Mapped[dict] = mapped_column(JSONB, default=list)
    parents: Mapped[dict] = mapped_column(JSONB, default=list)
    indexed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    
    source: Mapped["Source"] = relationship(back_populates="documents")
    chunks: Mapped[List["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
```

**models/chunk.py**:
```python
class Chunk(Base):
    __tablename__ = "chunks"
    
    chunk_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_id: Mapped[str] = mapped_column(ForeignKey("documents.file_id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)  # pgvector
    parent_heading: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    document: Mapped["Document"] = relationship(back_populates="chunks")
    
    __table_args__ = (
        Index("ix_chunks_file_id", "file_id"),
        Index("ix_chunks_embedding_hnsw", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
```

**models/index_job.py**:
```python
class IndexJob(Base):
    __tablename__ = "index_jobs"
    
    job_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # pending, running, completed, failed
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index("ix_index_jobs_status", "status"),
        Index("ix_index_jobs_source_id", "source_id"),
    )
```

### 3.2 Pydantic Schemas

**schemas/search.py**:
```python
class SearchFilters(BaseModel):
    source_ids: Optional[List[str]] = None
    mime_types: Optional[List[str]] = None
    modified_after: Optional[datetime] = None

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Optional[SearchFilters] = None

class SearchResult(BaseModel):
    chunk_id: str
    file_id: str
    file_name: str
    chunk_text: str
    chunk_index: int
    score: float
    web_view_link: str
    modified_time: datetime

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total: int
```

### 3.3 MCP Tool Schemas

**schemas/mcp.py**:
```python
class MCPSearchDocsInput(BaseModel):
    query: str
    max_results: int = 10
    filters: Optional[dict] = None

class MCPGetDocumentInput(BaseModel):
    file_id: str

class MCPListChangesInput(BaseModel):
    since: datetime

class MCPReindexSourceInput(BaseModel):
    source_id: str
    full_reindex: bool = False
```

---

## 4. Key Algorithms & Logic

### 4.1 Structure-Aware Chunking

**Algorithm** (services/chunking.py):
```python
def chunk_document(html_content: str, target_size: int = 600, overlap: int = 100) -> List[Chunk]:
    """
    1. Parse HTML to extract headings (h1-h6) and paragraphs
    2. Build hierarchy tree (track parent headings)
    3. Accumulate text under each heading
    4. When accumulated text exceeds target_size:
       - Split at sentence boundary
       - Create chunk with parent_heading metadata
       - Carry over last overlap tokens to next chunk
    5. Return list of chunks with metadata
    """
```

**Rationale**: Preserves semantic context, improves citation quality, respects document structure.

### 4.2 Hybrid Retrieval

**Algorithm** (services/retrieval.py):
```python
async def search(query: str, filters: SearchFilters, top_k: int = 10) -> List[SearchResult]:
    """
    1. Generate embedding for query using OpenAI API
    2. Build SQL query:
       - Vector similarity: embedding <=> query_embedding (pgvector cosine distance)
       - Metadata filters: source_id IN (...), mime_type IN (...), modified_time >= ...
       - Join chunks -> documents for metadata
    3. Execute with LIMIT top_k * 2 (fetch extra for reranking)
    4. (Optional) Rerank using cross-encoder
    5. Deduplicate by file_id (keep highest-scoring chunk per doc)
    6. Return top_k results with citations
    """
```

**Query Example**:
```sql
SELECT 
    c.chunk_id, c.chunk_text, c.chunk_index, c.parent_heading,
    d.file_id, d.file_name, d.web_view_link, d.modified_time,
    1 - (c.embedding <=> :query_embedding) AS score
FROM chunks c
JOIN documents d ON c.file_id = d.file_id
WHERE 
    d.source_id = ANY(:source_ids)
    AND d.mime_type = ANY(:mime_types)
    AND d.modified_time >= :modified_after
    AND d.is_deleted = false
ORDER BY c.embedding <=> :query_embedding
LIMIT :top_k;
```

### 4.3 Incremental Indexing

**Algorithm** (indexer/flows.py):
```python
@flow
async def incremental_update_flow(source_id: uuid.UUID):
    """
    1. Load source config and last startPageToken from DB
    2. Call Drive Changes API with pageToken
    3. For each change:
       - If file deleted: mark document.is_deleted = true, delete chunks
       - If file modified: reindex single document
       - If new file: index as new document
    4. Store new pageToken
    5. Update source.last_indexed_at
    """
```

**Error Handling**:
- Network errors: Exponential backoff (2^n seconds, max 5 retries)
- API quota exceeded: Pause and retry after quota reset
- Invalid file types: Log warning, skip file
- Embedding API errors: Retry with fallback model

---

## 5. API Contracts

### 5.1 Retrieval API Endpoints

**POST /api/v1/search**:
- **Request**: `SearchRequest` (Pydantic schema)
- **Response**: `SearchResponse` (200 OK)
- **Errors**: 400 (invalid query), 422 (validation error), 500 (server error)
- **Headers**: `X-Request-ID` for tracing

**GET /api/v1/documents/{file_id}**:
- **Response**: Document metadata + all chunks ordered by chunk_index
- **Errors**: 404 (document not found), 500

**GET /api/v1/changes?since={iso_datetime}**:
- **Response**: List of file_ids with modification timestamps
- **Query Params**: `since` (required), `limit` (default 100)

**POST /api/v1/reindex**:
- **Request**: `{"source_id": "uuid", "full_reindex": bool}`
- **Response**: `{"job_id": "uuid", "status": "pending"}`
- **Auth**: Admin API key required

**GET /health**:
- **Response**: `{"status": "healthy", "database": "ok", "embedding_api": "ok"}`

**GET /metrics**:
- **Response**: Prometheus text format
- **Metrics**:
  - `gdrive_rag_indexed_documents_total`
  - `gdrive_rag_indexed_chunks_total`
  - `gdrive_rag_search_requests_total`
  - `gdrive_rag_search_latency_seconds` (histogram)

### 5.2 MCP Server Endpoints

**POST /mcp** (SSE transport):
- **Protocol**: MCP JSON-RPC over SSE
- **Tools**: search_docs, get_document, list_recent_changes, reindex_source
- **Auth**: Bearer token in Authorization header

**GET /mcp/tools**:
- **Response**: JSON array of tool definitions (OpenAPI-like schemas)

---

## 6. Security Implementation

### 6.1 Authentication Flow

**Google Service Account**:
```python
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'),
        scopes=SCOPES
    )
    delegated_creds = creds.with_subject('admin@example.com')  # Domain admin
    return build('drive', 'v3', credentials=delegated_creds)
```

**MCP API Key**:
```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != os.getenv('MCP_API_KEY'):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
```

### 6.2 Secrets Management

**Environment Variables**:
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Path to service account JSON file
- `DATABASE_URL`: PostgreSQL connection string (with password)
- `OPENAI_API_KEY`: OpenAI API key
- `MCP_API_KEY`: Secret for MCP client authentication

**Production**: Use external secret manager (AWS Secrets Manager, Google Secret Manager, Vault)

### 6.3 Audit Logging

```python
import structlog

audit_log = structlog.get_logger("audit")

@app.post("/api/v1/search")
async def search_endpoint(request: SearchRequest, api_key: str = Depends(verify_api_key)):
    audit_log.info(
        "mcp_tool_invoked",
        tool="search_docs",
        query_hash=hashlib.sha256(request.query.encode()).hexdigest(),
        filters=request.filters,
        timestamp=datetime.utcnow().isoformat()
    )
    # ... implementation
```

---

## 7. Performance Optimizations

### 7.1 Database Optimizations

**Connection Pooling**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)
```

**Query Optimization**:
- Use HNSW index for vector search (faster than IVFFlat)
- Index metadata columns (source_id, modified_time, mime_type)
- Use EXPLAIN ANALYZE to validate query plans
- Consider covering indexes for hot queries

**Caching**:
- Cache embeddings for frequently searched queries (Redis, optional)
- Cache source configs in memory (reload on change)

### 7.2 Embedding API Optimizations

**Batching**:
```python
async def embed_texts(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """Process texts in batches of 100 to maximize throughput"""
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        response = await openai.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )
        embeddings.extend([e.embedding for e in response.data])
    return embeddings
```

**Rate Limiting**:
- Implement token bucket algorithm
- Respect OpenAI rate limits (500 requests/minute, 5M tokens/minute)

### 7.3 Indexer Optimizations

**Parallel Processing**:
- Use Prefect's `.map()` for parallel task execution
- Process multiple documents concurrently (limit: 10 concurrent tasks)

**Incremental Updates**:
- Use Drive Changes API instead of full crawls
- Store and reuse pageToken
- Only reindex changed files

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Coverage Target**: 80%+

**Key Test Modules**:
- `test_chunking.py`: Verify chunk boundaries, overlap, metadata
- `test_embedding.py`: Mock OpenAI API, test batching and retries
- `test_extractors.py`: Test content extraction for each file type
- `test_retrieval.py`: Test vector search logic (with in-memory DB)

**Example**:
```python
@pytest.mark.asyncio
async def test_chunking_respects_headings():
    html = "<h1>Introduction</h1><p>Text...</p><h2>Section</h2><p>More text...</p>"
    chunks = await chunk_document(html, target_size=100)
    
    assert len(chunks) >= 2
    assert chunks[0].parent_heading == "Introduction"
    assert chunks[1].parent_heading == "Section"
```

### 8.2 Integration Tests

**Setup**: Docker Compose with Postgres + pgvector + test services

**Key Tests**:
- `test_indexer.py`: End-to-end indexing flow (mock Google APIs)
- `test_retrieval.py`: Search with real database and embeddings
- `test_mcp.py`: MCP tool invocation with real API

**Example**:
```python
@pytest.mark.integration
async def test_full_indexing_flow(db_session, mock_drive_service):
    # Given a source configuration
    source = Source(name="test", type="folder", config={"folder_id": "123"})
    db_session.add(source)
    await db_session.commit()
    
    # When indexing is triggered
    await full_crawl_flow(source.id)
    
    # Then documents and chunks are created
    docs = await db_session.execute(select(Document))
    assert len(docs.scalars().all()) > 0
```

### 8.3 Verification Commands

**Linting**:
```bash
ruff check src/ tests/
ruff format --check src/ tests/
```

**Type Checking**:
```bash
mypy src/gdrive_rag --strict
```

**Tests**:
```bash
pytest tests/unit -v --cov=gdrive_rag --cov-report=term-missing
pytest tests/integration -v --maxfail=1
```

**Build Docker Image**:
```bash
docker build -f docker/Dockerfile.api -t gdrive-rag-api:latest .
docker build -f docker/Dockerfile.indexer -t gdrive-rag-indexer:latest .
```

---

## 9. Deployment Architecture

### 9.1 Components

**Retrieval API**:
- Container: `gdrive-rag-api:latest`
- Replicas: 2+ (horizontal scaling)
- Port: 8001 (internal)
- Resources: 512MB RAM, 0.5 CPU
- Environment: DATABASE_URL, OPENAI_API_KEY, LOG_LEVEL

**MCP Server**:
- Container: Same as Retrieval API (different process)
- Port: 8000 (exposed)
- Additional env: MCP_API_KEY

**Indexer**:
- Container: `gdrive-rag-indexer:latest`
- Replicas: 1 (singleton with leader election)
- Resources: 1GB RAM, 1 CPU
- Cron: Every 15 minutes (incremental update)
- Environment: DATABASE_URL, OPENAI_API_KEY, GOOGLE_SERVICE_ACCOUNT_JSON

**Database**:
- Managed PostgreSQL (RDS, Cloud SQL, or self-hosted)
- Storage: 50GB+ (grows with corpus)
- Backups: Daily automated backups
- Extensions: pgvector

### 9.2 Docker Compose (Local Development)

**docker-compose.yml**:
```yaml
version: '3.9'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: gdrive_rag
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/gdrive_rag
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
  
  mcp:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: uvicorn gdrive_rag.mcp.server:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/gdrive_rag
      MCP_API_KEY: ${MCP_API_KEY}
      RETRIEVAL_API_URL: http://api:8001
    depends_on:
      - api
  
  indexer:
    build:
      context: .
      dockerfile: docker/Dockerfile.indexer
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/gdrive_rag
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      GOOGLE_SERVICE_ACCOUNT_JSON: /secrets/service_account.json
    volumes:
      - ./secrets:/secrets
    depends_on:
      - postgres

volumes:
  postgres_data:
```

---

## 10. Delivery Phases

### Phase 1: Foundation (Week 1-2)
**Goal**: Database, core models, basic API structure

**Deliverables**:
- PostgreSQL schema with migrations (Alembic)
- SQLAlchemy models (Source, Document, Chunk, IndexJob)
- Pydantic schemas (SearchRequest, SearchResponse)
- FastAPI skeleton with /health endpoint
- Docker Compose setup for local development
- Basic test infrastructure (pytest, conftest.py)

**Verification**:
- ✅ `alembic upgrade head` creates all tables
- ✅ `pytest tests/unit/test_models.py` passes
- ✅ `docker-compose up` starts all services
- ✅ `curl http://localhost:8001/health` returns 200

---

### Phase 2: Google Drive Integration (Week 2-3)
**Goal**: Authenticate with Google, enumerate files, extract content

**Deliverables**:
- services/google_drive.py (Drive API client)
- extractors/ for Google Docs, PDF, DOCX
- Unit tests with mocked Google APIs
- Integration test with test Drive folder

**Verification**:
- ✅ Service account authenticates successfully
- ✅ List files from test folder works
- ✅ Extract text from Google Doc works
- ✅ pytest tests/unit/test_google_drive.py passes

---

### Phase 3: Chunking & Embedding (Week 3-4)
**Goal**: Structure-aware chunking, OpenAI embedding integration

**Deliverables**:
- services/chunking.py (HTML parsing, hierarchy tracking)
- services/embedding.py (OpenAI client with batching)
- Unit tests for chunking edge cases
- Integration test for embedding generation

**Verification**:
- ✅ Chunk document preserves headings
- ✅ Chunks have correct overlap
- ✅ Embeddings are 1536-dimensional
- ✅ pytest tests/unit/test_chunking.py passes

---

### Phase 4: Indexer Workflows (Week 4-5)
**Goal**: Full crawl and incremental update flows

**Deliverables**:
- indexer/flows.py (Prefect flows)
- indexer/tasks.py (atomic indexing tasks)
- Full crawl flow (enumerate → extract → chunk → embed → store)
- Incremental update flow (Changes API → selective reindex)
- IndexJob tracking and error handling

**Verification**:
- ✅ Full crawl indexes test folder (100 docs)
- ✅ Incremental update detects and reindexes changed file
- ✅ Failed tasks retry with backoff
- ✅ IndexJob records contain accurate stats

---

### Phase 5: Retrieval API (Week 5-6)
**Goal**: Vector search with metadata filtering

**Deliverables**:
- services/retrieval.py (hybrid search implementation)
- api/routes/search.py (POST /api/v1/search)
- api/routes/documents.py (GET /api/v1/documents/{file_id})
- api/routes/changes.py (GET /api/v1/changes)
- Integration tests with seeded database

**Verification**:
- ✅ Search returns relevant results (manual evaluation)
- ✅ Search with filters works correctly
- ✅ p95 latency < 1 second (load test with 100 concurrent requests)
- ✅ pytest tests/integration/test_retrieval.py passes

---

### Phase 6: MCP Server (Week 6-7)
**Goal**: Expose retrieval via MCP tools

**Deliverables**:
- mcp/server.py (FastAPI app with SSE transport)
- mcp/tools/ (search_docs, get_document, list_recent_changes, reindex_source)
- mcp.json manifest
- MCP client integration test (using Claude Desktop or test client)

**Verification**:
- ✅ MCP server responds to tool invocations
- ✅ search_docs returns correct format
- ✅ Claude Desktop successfully calls tools (manual test)
- ✅ pytest tests/integration/test_mcp.py passes

---

### Phase 7: Production Readiness (Week 7-8)
**Goal**: Observability, security, deployment

**Deliverables**:
- Structured logging with structlog
- Prometheus metrics endpoint
- Admin API key authentication
- Audit logging for all MCP calls
- Deployment documentation (Kubernetes manifests or Docker Compose prod)
- Performance benchmarks and tuning

**Verification**:
- ✅ /metrics endpoint returns valid Prometheus data
- ✅ Unauthorized requests return 401
- ✅ Audit logs capture all tool invocations
- ✅ Production deployment succeeds (staging environment)
- ✅ Load test: 100 req/s for 5 minutes with <1s p95 latency

---

## 11. Risk Mitigation

### 11.1 Google API Rate Limits
**Risk**: Exceeding Drive API quotas during large crawls

**Mitigation**:
- Implement exponential backoff (google-api-python-client built-in)
- Monitor quota usage via Cloud Console
- Add configurable delay between API calls (default: 100ms)
- Use batch API for file metadata (get 100 files in 1 request)

### 11.2 Embedding API Costs
**Risk**: High costs for large document corpora

**Mitigation**:
- Incremental indexing (only new/changed docs)
- Cache embeddings (never regenerate for unchanged content)
- Use text-embedding-3-small ($0.02/1M tokens, cheapest tier)
- Budget monitoring and alerts

### 11.3 Database Performance
**Risk**: Slow vector searches at scale (>100k chunks)

**Mitigation**:
- Use HNSW index (faster than IVFFlat)
- Tune `m` and `ef_construction` parameters
- Partition chunks table by source_id (if corpus >1M chunks)
- Monitor query plans and add indexes as needed

### 11.4 MCP Protocol Changes
**Risk**: Breaking changes in MCP specification

**Mitigation**:
- Use stable MCP SDK (when available)
- Pin SDK version in pyproject.toml
- Implement version negotiation in MCP server
- Maintain backward compatibility for 1 version

---

## 12. Success Criteria

### 12.1 Functional Success
- ✅ Index 10,000+ documents from production Drive
- ✅ Search returns relevant results (precision@10 ≥ 70%)
- ✅ All MCP tools work with Claude Desktop
- ✅ Incremental updates detect changes within 15 minutes
- ✅ Citations always include valid Drive links

### 12.2 Performance Success
- ✅ p95 search latency < 1 second
- ✅ Indexer processes 100+ docs/minute
- ✅ API handles 100 concurrent requests
- ✅ Database storage < 10GB for 10k documents

### 12.3 Quality Success
- ✅ Test coverage ≥ 80%
- ✅ mypy passes with --strict
- ✅ ruff linter reports 0 errors
- ✅ All integration tests pass in CI/CD
- ✅ Zero secrets in logs or error messages

---

## 13. Future Enhancements

**Post-MVP**:
1. **Multi-tenant support**: Separate indexes per organization
2. **User-level ACLs**: Check Drive permissions at query time
3. **Advanced chunking**: Semantic sectioning, entity-aware splitting
4. **BM25 + vector hybrid**: Improve long-tail query recall
5. **Real-time indexing**: Drive push notifications instead of polling
6. **Query analytics**: Track search quality and improve ranking
7. **Additional sources**: Confluence, Notion, SharePoint connectors
8. **Self-hosted embeddings**: Support for sentence-transformers in airgapped environments

---

**Specification Status**: ✅ Ready for Planning Phase  
**Next Step**: Create detailed implementation plan in plan.md
