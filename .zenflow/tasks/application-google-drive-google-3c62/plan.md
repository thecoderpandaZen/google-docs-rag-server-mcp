# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 3b46d26e-f3d9-4a09-b6a1-0afc035f8d5d -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: 69d4c6aa-0acb-4ab1-bd36-8bd094e02c5b -->

Create a technical specification based on the PRD in `{@artifacts_path}/requirements.md`.

1. Review existing codebase architecture and identify reusable components
2. Define the implementation approach

Save to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach referencing existing code patterns
- Source code structure changes
- Data model / API / interface changes
- Delivery phases (incremental, testable milestones)
- Verification approach using project lint/test commands

### [x] Step: Planning
<!-- chat-id: fd655bdd-4ea4-4793-a970-5489f562b40a -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

---

## Implementation Tasks

### Phase 1: Foundation (Database, Models, API Structure)

#### [ ] Task 1.1: Project Setup
**Description**: Initialize Python project with pyproject.toml and dependencies

**Steps**:
- Create project structure: `src/gdrive_rag/` with `__init__.py`
- Create `pyproject.toml` with all dependencies from spec (FastAPI, SQLAlchemy, asyncpg, pgvector, Prefect, etc.)
- Create `src/gdrive_rag/config.py` for centralized configuration
- Create `tests/` directory with `conftest.py`
- Create `.gitignore` for Python projects

**Verification**:
- ✅ `python -m pip install -e .` installs successfully
- ✅ All required dependencies are listed in pyproject.toml

#### [ ] Task 1.2: Database Models
**Description**: Implement SQLAlchemy models per spec section 3.1

**Steps**:
- Create `src/gdrive_rag/models/base.py` with Base declarative model
- Create `src/gdrive_rag/models/source.py` with Source model
- Create `src/gdrive_rag/models/document.py` with Document model
- Create `src/gdrive_rag/models/chunk.py` with Chunk model (including pgvector Vector type)
- Create `src/gdrive_rag/models/index_job.py` with IndexJob model
- Create `src/gdrive_rag/models/__init__.py` exporting all models

**Verification**:
- ✅ Models match schema in spec section 3.1
- ✅ HNSW index defined on chunks.embedding
- ✅ All foreign key relationships defined correctly

#### [ ] Task 1.3: Database Migrations
**Description**: Setup Alembic for database migrations

**Steps**:
- Initialize Alembic: `alembic init src/gdrive_rag/db/migrations`
- Configure `alembic.ini` with async database URL
- Update `env.py` to use async engine and import models
- Create initial migration: `alembic revision --autogenerate -m "initial schema"`
- Add pgvector extension creation to migration

**Verification**:
- ✅ `alembic upgrade head` creates all tables in Postgres
- ✅ pgvector extension is enabled
- ✅ HNSW index is created on chunks table

#### [ ] Task 1.4: Pydantic Schemas
**Description**: Create Pydantic schemas for API validation

**Steps**:
- Create `src/gdrive_rag/schemas/search.py` (SearchRequest, SearchResponse, SearchResult, SearchFilters)
- Create `src/gdrive_rag/schemas/document.py` (DocumentResponse, DocumentMetadata)
- Create `src/gdrive_rag/schemas/mcp.py` (MCP tool input/output schemas)
- Create `src/gdrive_rag/schemas/__init__.py`

**Verification**:
- ✅ Schemas match spec section 3.2
- ✅ Proper validation rules (min_length, max_length, ge, le)
- ✅ All schemas use Pydantic v2 syntax

#### [ ] Task 1.5: Database Session Management
**Description**: Setup async database session and connection pooling

**Steps**:
- Create `src/gdrive_rag/db/__init__.py`
- Create `src/gdrive_rag/db/session.py` with async engine and session factory
- Configure connection pool (size=20, max_overflow=10)
- Create dependency injection for FastAPI: `get_db()`

**Verification**:
- ✅ Connection pool parameters match spec section 7.1
- ✅ Sessions properly close after use

#### [ ] Task 1.6: FastAPI Application Skeleton
**Description**: Create basic FastAPI app with health endpoint

**Steps**:
- Create `src/gdrive_rag/api/main.py` with FastAPI app
- Create `src/gdrive_rag/api/__init__.py`
- Create `src/gdrive_rag/api/deps.py` for common dependencies
- Add `/health` endpoint that checks DB connectivity
- Configure CORS, logging, and middleware

**Verification**:
- ✅ `uvicorn gdrive_rag.api.main:app --reload` starts successfully
- ✅ `curl http://localhost:8001/health` returns 200 with status

#### [ ] Task 1.7: Docker Compose Setup
**Description**: Create Docker Compose for local development

**Steps**:
- Create `docker/docker-compose.yml` with postgres (pgvector/pgvector:pg15) service
- Configure environment variables
- Create `docker/Dockerfile.api` for API service
- Create `docker/Dockerfile.indexer` for indexer service
- Add volumes for persistent storage

**Verification**:
- ✅ `docker-compose up` starts postgres with pgvector
- ✅ Can connect to postgres at localhost:5432
- ✅ pgvector extension is available

#### [ ] Task 1.8: Testing Infrastructure
**Description**: Setup pytest with async support

**Steps**:
- Create `tests/conftest.py` with fixtures (db_session, client, etc.)
- Configure pytest.ini or pyproject.toml with asyncio mode
- Create `tests/unit/test_models.py` with basic model tests
- Setup test database fixtures

**Verification**:
- ✅ `pytest tests/unit/test_models.py -v` passes
- ✅ Test database is created and torn down properly

---

### Phase 2: Google Drive Integration

#### [ ] Task 2.1: Google Drive Service
**Description**: Implement Google Drive API client wrapper

**Steps**:
- Create `src/gdrive_rag/services/__init__.py`
- Create `src/gdrive_rag/services/google_drive.py`
- Implement authentication with service account
- Implement `list_files(folder_id, mime_types)` method
- Implement `get_file_metadata(file_id)` method
- Implement exponential backoff for API errors

**Verification**:
- ✅ Service account authenticates successfully
- ✅ Can list files from a test folder
- ✅ Retry logic works for transient failures

#### [ ] Task 2.2: Google Drive Changes API
**Description**: Implement change tracking using Changes API

**Steps**:
- Add `get_start_page_token()` method to google_drive.py
- Add `list_changes(page_token)` method
- Add logic to store and retrieve page tokens from DB
- Implement change type detection (created, modified, deleted)

**Verification**:
- ✅ Can retrieve startPageToken
- ✅ Can detect changes since a given token
- ✅ Change types are correctly identified

#### [ ] Task 2.3: Content Extractors - Base
**Description**: Create base extractor interface

**Steps**:
- Create `src/gdrive_rag/indexer/extractors/__init__.py`
- Create `src/gdrive_rag/indexer/extractors/base.py` with abstract Extractor class
- Define `extract(file_id, mime_type) -> str` interface
- Add error handling patterns

**Verification**:
- ✅ Base class defines clear interface
- ✅ Error handling is consistent

#### [ ] Task 2.4: Content Extractors - Google Docs
**Description**: Implement Google Docs text extraction

**Steps**:
- Create `src/gdrive_rag/indexer/extractors/gdoc.py`
- Use Google Docs API to export as HTML
- Parse HTML to extract text with structure (headings, paragraphs)
- Handle empty documents and errors

**Verification**:
- ✅ Can extract text from Google Doc
- ✅ Headings are preserved
- ✅ Empty docs handled gracefully

#### [ ] Task 2.5: Content Extractors - PDF
**Description**: Implement PDF text extraction

**Steps**:
- Create `src/gdrive_rag/indexer/extractors/pdf.py`
- Download PDF bytes from Drive
- Extract text using PyPDF2 or pdfplumber
- Handle password-protected and image-only PDFs

**Verification**:
- ✅ Can extract text from standard PDF
- ✅ Errors logged for problematic PDFs

#### [ ] Task 2.6: Content Extractors - DOCX
**Description**: Implement DOCX text extraction

**Steps**:
- Create `src/gdrive_rag/indexer/extractors/docx.py`
- Download DOCX bytes from Drive
- Extract text using python-docx
- Preserve heading hierarchy

**Verification**:
- ✅ Can extract text from DOCX
- ✅ Headings are preserved

#### [ ] Task 2.7: Google Drive Tests
**Description**: Unit tests for Google Drive integration

**Steps**:
- Create `tests/unit/test_google_drive.py`
- Mock Google API responses
- Test file listing, metadata retrieval
- Test error handling and retries

**Verification**:
- ✅ All tests pass
- ✅ Mocks correctly simulate Google API

---

### Phase 3: Chunking & Embedding

#### [ ] Task 3.1: Chunking Service
**Description**: Implement structure-aware chunking per spec section 4.1

**Steps**:
- Create `src/gdrive_rag/services/chunking.py`
- Implement HTML/Markdown parsing with BeautifulSoup or similar
- Build heading hierarchy tree
- Implement chunking algorithm (target_size=600, overlap=100)
- Preserve parent_heading metadata for each chunk

**Verification**:
- ✅ Chunks respect heading boundaries
- ✅ Overlap is correctly implemented
- ✅ Parent heading metadata is preserved

#### [ ] Task 3.2: Chunking Tests
**Description**: Comprehensive tests for chunking edge cases

**Steps**:
- Create `tests/unit/test_chunking.py`
- Test with various document structures (nested headings, long paragraphs)
- Test edge cases (very short docs, no headings, huge paragraphs)
- Verify overlap calculations

**Verification**:
- ✅ All tests pass
- ✅ Edge cases handled correctly

#### [ ] Task 3.3: Embedding Service
**Description**: Implement OpenAI embedding generation with batching

**Steps**:
- Create `src/gdrive_rag/services/embedding.py`
- Implement OpenAI client initialization
- Implement `embed_texts(texts: List[str])` with batching (100 per request)
- Add rate limiting and retry logic
- Add token counting and cost estimation logging

**Verification**:
- ✅ Embeddings are 1536-dimensional
- ✅ Batching works correctly (tests with 250 texts)
- ✅ Rate limiting prevents API errors

#### [ ] Task 3.4: Embedding Tests
**Description**: Unit tests for embedding service

**Steps**:
- Create `tests/unit/test_embedding.py`
- Mock OpenAI API responses
- Test batching logic
- Test retry on transient failures
- Test rate limiting

**Verification**:
- ✅ All tests pass
- ✅ Batching correctly splits large lists

---

### Phase 4: Indexer Workflows

#### [ ] Task 4.1: Prefect Tasks - File Enumeration
**Description**: Create Prefect task for enumerating files

**Steps**:
- Create `src/gdrive_rag/indexer/__init__.py`
- Create `src/gdrive_rag/indexer/tasks.py`
- Implement `enumerate_files` task that lists files from a source
- Add retry configuration (max_retries=3, retry_delay_seconds=60)

**Verification**:
- ✅ Task successfully lists files
- ✅ Retries work on failures

#### [ ] Task 4.2: Prefect Tasks - Content Extraction
**Description**: Create Prefect task for extracting content

**Steps**:
- Add `extract_content` task to tasks.py
- Route to appropriate extractor based on MIME type
- Handle extraction errors gracefully
- Return structured result (file_id, content, metadata)

**Verification**:
- ✅ Task extracts content correctly
- ✅ Errors are logged and task retries

#### [ ] Task 4.3: Prefect Tasks - Chunking
**Description**: Create Prefect task for chunking documents

**Steps**:
- Add `chunk_document` task to tasks.py
- Call chunking service
- Return list of chunks with metadata

**Verification**:
- ✅ Task chunks documents correctly
- ✅ Chunk metadata is complete

#### [ ] Task 4.4: Prefect Tasks - Embedding
**Description**: Create Prefect task for generating embeddings

**Steps**:
- Add `generate_embeddings` task to tasks.py
- Call embedding service with batching
- Handle API failures with retries

**Verification**:
- ✅ Task generates embeddings correctly
- ✅ Batching works for large chunk lists

#### [ ] Task 4.5: Prefect Tasks - Database Upsert
**Description**: Create Prefect task for storing chunks in DB

**Steps**:
- Add `upsert_chunks` task to tasks.py
- Implement idempotent upsert logic (delete old chunks, insert new)
- Update document metadata
- Handle database errors

**Verification**:
- ✅ Task upserts chunks correctly
- ✅ Idempotency: running twice produces same result

#### [ ] Task 4.6: Prefect Flow - Full Crawl
**Description**: Implement full crawl flow

**Steps**:
- Create `src/gdrive_rag/indexer/flows.py`
- Implement `full_crawl_flow(source_id)` using tasks
- Create IndexJob record at start, update at end
- Handle errors and update job status
- Log statistics (files processed, chunks created)

**Verification**:
- ✅ Flow completes for test folder (10+ documents)
- ✅ Documents and chunks stored in DB
- ✅ IndexJob record shows correct stats

#### [ ] Task 4.7: Prefect Flow - Incremental Update
**Description**: Implement incremental update flow

**Steps**:
- Add `incremental_update_flow(source_id)` to flows.py
- Use Changes API to detect changes
- For each change: delete old chunks (if modified/deleted), reindex (if modified/created)
- Update page token after successful completion

**Verification**:
- ✅ Flow detects and processes changed files
- ✅ Deleted files are marked is_deleted=true
- ✅ Modified files are reindexed

#### [ ] Task 4.8: Indexer Tests
**Description**: Integration tests for indexing workflows

**Steps**:
- Create `tests/integration/test_indexer.py`
- Mock Google APIs
- Test full crawl flow end-to-end
- Test incremental update flow
- Test error handling and retries

**Verification**:
- ✅ All integration tests pass
- ✅ Database state is correct after flows

---

### Phase 5: Retrieval API

#### [ ] Task 5.1: Retrieval Service
**Description**: Implement hybrid vector search per spec section 4.2

**Steps**:
- Create `src/gdrive_rag/services/retrieval.py`
- Implement `search(query, filters, top_k)` method
- Generate query embedding
- Build SQL query with pgvector cosine similarity
- Apply metadata filters (source_id, mime_type, modified_after)
- Return ranked results with citations

**Verification**:
- ✅ Search returns relevant results (manual check)
- ✅ Metadata filters work correctly
- ✅ Results include all required fields

#### [ ] Task 5.2: Search Endpoint
**Description**: Implement POST /api/v1/search

**Steps**:
- Create `src/gdrive_rag/api/routes/__init__.py`
- Create `src/gdrive_rag/api/routes/search.py`
- Implement search endpoint using retrieval service
- Add request validation with Pydantic
- Add response formatting
- Register route in main.py

**Verification**:
- ✅ Endpoint returns 200 with valid request
- ✅ Validation errors return 422
- ✅ Results match expected schema

#### [ ] Task 5.3: Document Retrieval Endpoint
**Description**: Implement GET /api/v1/documents/{file_id}

**Steps**:
- Create `src/gdrive_rag/api/routes/documents.py`
- Implement document retrieval endpoint
- Return document metadata + all chunks ordered by chunk_index
- Handle 404 for missing documents

**Verification**:
- ✅ Endpoint returns document with chunks
- ✅ 404 for non-existent file_id
- ✅ Chunks are ordered correctly

#### [ ] Task 5.4: Changes Endpoint
**Description**: Implement GET /api/v1/changes

**Steps**:
- Create `src/gdrive_rag/api/routes/changes.py`
- Implement changes listing endpoint
- Filter by since timestamp
- Add pagination support (limit, offset)

**Verification**:
- ✅ Returns changed documents since timestamp
- ✅ Pagination works correctly

#### [ ] Task 5.5: Admin Reindex Endpoint
**Description**: Implement POST /api/v1/reindex

**Steps**:
- Create `src/gdrive_rag/api/routes/admin.py`
- Implement reindex trigger endpoint
- Create IndexJob and trigger Prefect flow
- Add admin authentication check
- Return job_id and status

**Verification**:
- ✅ Endpoint triggers reindex flow
- ✅ Returns valid job_id
- ✅ Unauthorized requests return 401

#### [ ] Task 5.6: Retrieval API Tests
**Description**: Integration tests for retrieval API

**Steps**:
- Create `tests/integration/test_retrieval.py`
- Setup test database with seeded data
- Test search endpoint with various filters
- Test document retrieval endpoint
- Test changes endpoint
- Test error cases (invalid input, not found)

**Verification**:
- ✅ All integration tests pass
- ✅ Search returns expected results

#### [ ] Task 5.7: Performance Testing
**Description**: Verify p95 latency < 1 second

**Steps**:
- Create performance test script using locust or similar
- Seed database with 1000+ documents
- Run load test with 100 concurrent requests
- Measure p95 latency

**Verification**:
- ✅ p95 latency < 1 second
- ✅ No errors under load

---

### Phase 6: MCP Server

#### [ ] Task 6.1: MCP Server Skeleton
**Description**: Create basic MCP server structure

**Steps**:
- Create `src/gdrive_rag/mcp/__init__.py`
- Create `src/gdrive_rag/mcp/server.py` with FastAPI app
- Setup SSE transport for MCP JSON-RPC
- Add authentication middleware (Bearer token)
- Add tool registration endpoint GET /mcp/tools

**Verification**:
- ✅ Server starts successfully
- ✅ /mcp/tools returns tool definitions
- ✅ Authentication works

#### [ ] Task 6.2: MCP Tool - search_docs
**Description**: Implement search_docs tool

**Steps**:
- Create `src/gdrive_rag/mcp/tools/__init__.py`
- Create `src/gdrive_rag/mcp/tools/search_docs.py`
- Implement tool that calls Retrieval API /search
- Define input/output schemas
- Add error handling and logging

**Verification**:
- ✅ Tool responds to invocations
- ✅ Returns correctly formatted results
- ✅ Errors are handled gracefully

#### [ ] Task 6.3: MCP Tool - get_document
**Description**: Implement get_document tool

**Steps**:
- Create `src/gdrive_rag/mcp/tools/get_document.py`
- Implement tool that calls Retrieval API /documents/{file_id}
- Define input/output schemas
- Add error handling

**Verification**:
- ✅ Tool retrieves documents correctly
- ✅ Returns full document with chunks

#### [ ] Task 6.4: MCP Tool - list_recent_changes
**Description**: Implement list_recent_changes tool

**Steps**:
- Create `src/gdrive_rag/mcp/tools/list_changes.py`
- Implement tool that calls Retrieval API /changes
- Define input/output schemas
- Add error handling

**Verification**:
- ✅ Tool returns recent changes correctly
- ✅ Timestamp filtering works

#### [ ] Task 6.5: MCP Tool - reindex_source
**Description**: Implement reindex_source admin tool

**Steps**:
- Create `src/gdrive_rag/mcp/tools/reindex_source.py`
- Implement tool that calls Retrieval API /reindex
- Add admin role check
- Define input/output schemas

**Verification**:
- ✅ Tool triggers reindex correctly
- ✅ Admin-only access enforced

#### [ ] Task 6.6: MCP Configuration
**Description**: Create mcp.json manifest

**Steps**:
- Create `mcp.json` at repository root
- Define server configuration per spec section FR-16
- Configure SSE transport
- Add environment variable references

**Verification**:
- ✅ mcp.json is valid JSON
- ✅ Configuration matches spec

#### [ ] Task 6.7: MCP Integration Tests
**Description**: End-to-end tests for MCP server

**Steps**:
- Create `tests/integration/test_mcp.py`
- Test each MCP tool invocation
- Test authentication
- Test error handling
- Mock Retrieval API responses

**Verification**:
- ✅ All MCP tools work correctly
- ✅ Authentication is enforced
- ✅ Errors are properly formatted

---

### Phase 7: Production Readiness

#### [ ] Task 7.1: Structured Logging
**Description**: Implement structured logging with structlog

**Steps**:
- Create `src/gdrive_rag/utils/__init__.py`
- Create `src/gdrive_rag/utils/logging.py`
- Configure structlog with JSON output
- Add request ID middleware
- Add logging to all services

**Verification**:
- ✅ Logs are in JSON format
- ✅ Request IDs are included
- ✅ Log levels work correctly

#### [ ] Task 7.2: Prometheus Metrics
**Description**: Add Prometheus metrics endpoint

**Steps**:
- Create `src/gdrive_rag/utils/metrics.py`
- Add prometheus-client metrics:
  - gdrive_rag_indexed_documents_total
  - gdrive_rag_indexed_chunks_total
  - gdrive_rag_search_requests_total
  - gdrive_rag_search_latency_seconds (histogram)
- Add GET /metrics endpoint to API
- Instrument all endpoints and services

**Verification**:
- ✅ /metrics returns Prometheus format
- ✅ Metrics are updated correctly

#### [ ] Task 7.3: Audit Logging
**Description**: Implement audit logs for all MCP tool calls

**Steps**:
- Add audit logging decorator for MCP tools
- Log: timestamp, tool name, query hash (not full query), user ID, result count
- Store audit logs separately or in database
- Never log full queries or sensitive data

**Verification**:
- ✅ All MCP calls are audited
- ✅ No sensitive data in logs

#### [ ] Task 7.4: Security Hardening
**Description**: Add API key authentication and security headers

**Steps**:
- Implement API key verification for Retrieval API
- Add security headers (CORS, CSP, etc.)
- Ensure no secrets in logs or error messages
- Add rate limiting (optional)

**Verification**:
- ✅ Unauthorized requests return 401
- ✅ Security headers present
- ✅ No secrets in logs

#### [ ] Task 7.5: Source Configuration
**Description**: Create sources.yaml for indexing sources

**Steps**:
- Create `sources.yaml` with example source configurations
- Document source types (folder, shared_drive)
- Add validation for source config

**Verification**:
- ✅ Example sources.yaml is valid
- ✅ Documentation is clear

#### [ ] Task 7.6: Documentation
**Description**: Create deployment and operation documentation

**Steps**:
- Create `README.md` with project overview, setup, usage
- Document environment variables
- Document API endpoints (link to OpenAPI)
- Document MCP tools
- Create deployment guide (Docker Compose, Kubernetes)

**Verification**:
- ✅ README is comprehensive
- ✅ Setup instructions work

#### [ ] Task 7.7: Code Quality
**Description**: Setup linting and type checking

**Steps**:
- Configure ruff in pyproject.toml
- Configure mypy with strict mode
- Add pre-commit hooks (optional)
- Run linters and fix all issues

**Verification**:
- ✅ `ruff check src/ tests/` reports 0 errors
- ✅ `ruff format --check src/ tests/` passes
- ✅ `mypy src/gdrive_rag --strict` passes

#### [ ] Task 7.8: Test Coverage
**Description**: Ensure test coverage ≥ 80%

**Steps**:
- Run `pytest --cov=gdrive_rag --cov-report=term-missing`
- Add tests for uncovered code
- Reach ≥80% coverage

**Verification**:
- ✅ Coverage ≥ 80%
- ✅ All critical paths tested

#### [ ] Task 7.9: Production Deployment
**Description**: Deploy to staging/production environment

**Steps**:
- Build Docker images for API and Indexer
- Deploy to staging with docker-compose or Kubernetes
- Run end-to-end smoke tests
- Monitor logs and metrics
- Document deployment process

**Verification**:
- ✅ Services start successfully
- ✅ Health checks pass
- ✅ Can index and search documents
- ✅ MCP tools work with Claude Desktop

---

## Verification Summary

After completing all tasks, verify the following success criteria from spec section 12:

### Functional Success
- [ ] Index 10,000+ documents from production Drive
- [ ] Search returns relevant results (precision@10 ≥ 70%)
- [ ] All MCP tools work with Claude Desktop
- [ ] Incremental updates detect changes within 15 minutes
- [ ] Citations always include valid Drive links

### Performance Success
- [ ] p95 search latency < 1 second
- [ ] Indexer processes 100+ docs/minute
- [ ] API handles 100 concurrent requests
- [ ] Database storage < 10GB for 10k documents

### Quality Success
- [ ] Test coverage ≥ 80%
- [ ] mypy passes with --strict
- [ ] ruff linter reports 0 errors
- [ ] All integration tests pass in CI/CD
- [ ] Zero secrets in logs or error messages
