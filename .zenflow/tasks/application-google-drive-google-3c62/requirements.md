# Product Requirements Document: Google Drive RAG Server with MCP

## 1. Overview

### 1.1 Product Vision
A production-ready, enterprise-grade Retrieval-Augmented Generation (RAG) system that indexes Google Drive and Google Docs content, exposing organizational knowledge to AI agents through Model Context Protocol (MCP) tools.

### 1.2 Goals
- Enable AI agents to reliably search and retrieve organizational knowledge from Google Drive
- Maintain citation provenance for all retrieved content
- Provide audit trails for all document access
- Support continuous incremental indexing with minimal latency
- Deliver sub-second query response times for typical searches

### 1.3 Non-Goals (Out of Scope for v1)
- Real-time collaboration features
- Document editing or modification capabilities
- Multi-tenant support (single organization only)
- Advanced analytics or usage dashboards
- Integration with non-Google document sources

---

## 2. Technical Decisions

### 2.1 Core Technology Stack
- **Language**: Python 3.11+
- **Deployment**: Container-based (Docker/Kubernetes)
- **Vector Store**: Postgres 15+ with pgvector extension
- **Orchestration**: Prefect 2.x (recommended) or Apache Airflow 2.x
- **MCP Transport**: HTTP with Server-Sent Events (SSE)
- **Embedding Model**: OpenAI text-embedding-3-small (primary), with optional self-hosted fallback using sentence-transformers
- **Chunking Strategy**: Structure-aware chunking respecting document hierarchy (headings, sections) with semantic boundaries

### 2.2 Rationale

**Postgres + pgvector**: 
- Single operational dependency reduces complexity
- Excellent performance for 10k-1M document scale
- ACID guarantees for metadata consistency
- Hybrid search (vector + full-text) in one system

**Prefect over Airflow**:
- Lighter weight and faster iteration
- Better Python-native experience
- Simpler deployment for indexing workflows
- Adequate retry/monitoring for this use case
- (Airflow acceptable if organization standardized on it)

**OpenAI Embeddings**:
- Industry-leading quality-to-cost ratio
- text-embedding-3-small: 1536 dims, $0.02/1M tokens
- Managed service reduces ops burden
- Fallback to sentence-transformers (all-mpnet-base-v2) for air-gapped deployments

**Structure-Aware Chunking**:
- Preserves document context (headers remain with content)
- Improves retrieval relevance
- Better citation granularity

---

## 3. User Stories & Use Cases

### 3.1 Primary Personas
1. **AI Agent** - Claude or other LLM-based agent using MCP tools
2. **Knowledge Worker** - End user whose queries are served by the agent
3. **Administrator** - Manages indexing sources and monitors system health

### 3.2 Core User Stories

**US-1: Semantic Search**
- **As an** AI agent
- **I want to** search organizational knowledge using natural language queries
- **So that** I can augment my responses with accurate, cited information

**US-2: Document Retrieval**
- **As an** AI agent
- **I want to** retrieve full document content by file ID
- **So that** I can access comprehensive context for specific documents

**US-3: Change Tracking**
- **As an** AI agent
- **I want to** discover recently modified documents
- **So that** I can provide up-to-date information

**US-4: Source Management**
- **As an** administrator
- **I want to** configure which Drive folders/shared drives are indexed
- **So that** I can control knowledge scope and access

**US-5: Citation Provenance**
- **As a** knowledge worker
- **I want** every retrieved answer to include source document links
- **So that** I can verify information and explore further

---

## 4. Functional Requirements

### 4.1 Indexing System

**FR-1: Google Drive Authentication**
- System authenticates using Service Account with domain-wide delegation
- Supports Google Workspace domains
- Credentials managed via environment variables or secret management

**FR-2: Source Configuration**
- Administrators define indexing sources via configuration file (YAML/JSON)
- Each source specifies:
  - Source type: folder ID, shared drive ID, or file list
  - Inclusion/exclusion patterns (glob-style)
  - Allowed MIME types
  - Update frequency

**FR-3: Content Extraction**
- Support file types:
  - Google Docs → export to plain text/HTML
  - Google Sheets → export to CSV/plain text (optional, configurable)
  - Google Slides → extract slide text
  - PDF → extract text via PyPDF2 or pdfplumber
  - DOCX → extract via python-docx
- Skip or log errors for unsupported types
- Preserve basic formatting (headings, lists) where possible

**FR-4: Text Chunking**
- Chunk documents using structure-aware strategy:
  - Respect heading hierarchy (H1, H2, H3)
  - Target chunk size: 500-800 tokens
  - Overlap: 100-150 tokens between chunks
  - Preserve metadata (chunk index, parent heading)
- Each chunk stored with:
  - chunk_id (UUID)
  - chunk_index (ordinal position)
  - chunk_text (content)
  - embedding_vector (1536 dims for OpenAI)

**FR-5: Embedding Generation**
- Generate embeddings using OpenAI text-embedding-3-small API
- Batch processing (up to 100 texts per request)
- Retry logic with exponential backoff
- Rate limiting compliance

**FR-6: Incremental Updates**
- Use Google Drive Changes API for change detection
- Store `startPageToken` after initial crawl
- Poll for changes every 5-15 minutes (configurable)
- Update/delete affected chunks only
- Log all indexing operations for audit

**FR-7: Index Storage**
- Store in Postgres database with schema:
  - `documents` table: file metadata
  - `chunks` table: chunk content and embeddings
  - `sources` table: source configurations
  - `index_jobs` table: job history and state
- Use pgvector for efficient similarity search

### 4.2 Retrieval API

**FR-8: Semantic Search Endpoint**
- HTTP POST `/api/v1/search`
- Request body:
  ```json
  {
    "query": "string",
    "top_k": 10,
    "filters": {
      "source_ids": ["source1"],
      "mime_types": ["application/vnd.google-apps.document"],
      "modified_after": "2024-01-01T00:00:00Z"
    }
  }
  ```
- Response:
  ```json
  {
    "results": [
      {
        "chunk_id": "uuid",
        "file_id": "google_file_id",
        "file_name": "Document Title",
        "chunk_text": "...",
        "chunk_index": 0,
        "score": 0.85,
        "web_view_link": "https://docs.google.com/...",
        "modified_time": "2024-12-01T10:00:00Z"
      }
    ]
  }
  ```

**FR-9: Document Retrieval Endpoint**
- HTTP GET `/api/v1/documents/{file_id}`
- Returns all chunks for a document, ordered by chunk_index
- Includes full metadata

**FR-10: Recent Changes Endpoint**
- HTTP GET `/api/v1/changes?since={timestamp}`
- Returns list of modified/deleted file IDs since given time
- Supports pagination

**FR-11: Hybrid Search**
- Combine vector similarity with metadata filters
- Optional full-text search fallback using Postgres tsvector
- Configurable score thresholds

### 4.3 MCP Server

**FR-12: MCP Tool: search_docs**
- **Input schema**:
  ```json
  {
    "query": "string (required)",
    "max_results": "integer (optional, default 10)",
    "filters": {
      "source_ids": ["string"],
      "file_types": ["string"],
      "modified_after": "ISO8601 datetime"
    }
  }
  ```
- **Output**: Array of search results with citations
- Maps to Retrieval API `/search` endpoint

**FR-13: MCP Tool: get_document**
- **Input schema**:
  ```json
  {
    "file_id": "string (required)"
  }
  ```
- **Output**: Full document metadata and chunked content
- Maps to Retrieval API `/documents/{file_id}` endpoint

**FR-14: MCP Tool: list_recent_changes**
- **Input schema**:
  ```json
  {
    "since": "ISO8601 datetime (required)"
  }
  ```
- **Output**: List of changed documents
- Maps to Retrieval API `/changes` endpoint

**FR-15: MCP Tool: reindex_source** (Admin)
- **Input schema**:
  ```json
  {
    "source_id": "string (required)",
    "full_reindex": "boolean (optional, default false)"
  }
  ```
- **Output**: Job handle/status
- Triggers indexer workflow

**FR-16: MCP Configuration**
- Server declared in `mcp.json`:
  ```json
  {
    "mcpServers": {
      "gdrive-rag": {
        "url": "http://localhost:8000/mcp",
        "transport": "sse"
      }
    }
  }
  ```

### 4.4 Operational Requirements

**FR-17: Health Checks**
- `/health` endpoint returns system status
- Checks: DB connectivity, embedding API availability, recent index age

**FR-18: Metrics & Observability**
- Prometheus-compatible metrics endpoint
- Key metrics:
  - Total indexed documents/chunks
  - Search request latency (p50, p95, p99)
  - Indexing job success/failure rates
  - Embedding API call counts

**FR-19: Logging**
- Structured JSON logs (using structlog or similar)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Include request IDs for tracing

**FR-20: Configuration Management**
- Environment-based configuration (12-factor)
- Separate configs for dev/staging/prod
- Secret management via environment variables or secret providers

---

## 5. Non-Functional Requirements

### 5.1 Performance
- **NFR-1**: Search queries return results in <1 second (p95)
- **NFR-2**: Support 10,000+ documents with room to scale to 100,000+
- **NFR-3**: Indexer processes 100 documents/minute minimum

### 5.2 Reliability
- **NFR-4**: 99.5% uptime for retrieval API
- **NFR-5**: Indexer failures auto-retry with exponential backoff
- **NFR-6**: Graceful degradation if embedding API is unavailable

### 5.3 Security
- **NFR-7**: All API endpoints require authentication (API keys or OAuth)
- **NFR-8**: TLS 1.3 for all external communications
- **NFR-9**: Secrets never logged or exposed in error messages
- **NFR-10**: Audit log for all MCP tool invocations

### 5.4 Scalability
- **NFR-11**: Horizontal scaling for retrieval API (stateless design)
- **NFR-12**: Database connection pooling to handle concurrent queries
- **NFR-13**: Support for distributed indexing (multiple workers)

### 5.5 Maintainability
- **NFR-14**: Comprehensive unit and integration tests (>80% coverage)
- **NFR-15**: Type hints throughout Python codebase
- **NFR-16**: OpenAPI/Swagger documentation for all HTTP APIs
- **NFR-17**: Container images <500MB compressed

---

## 6. Data Model

### 6.1 Database Schema (Postgres)

**Table: sources**
```sql
id: UUID (PK)
name: VARCHAR(255)
type: VARCHAR(50)  -- 'folder', 'shared_drive', 'file_list'
config: JSONB  -- source-specific configuration
created_at: TIMESTAMP
updated_at: TIMESTAMP
last_indexed_at: TIMESTAMP
```

**Table: documents**
```sql
file_id: VARCHAR(255) (PK)
source_id: UUID (FK -> sources.id)
file_name: VARCHAR(1024)
mime_type: VARCHAR(128)
web_view_link: TEXT
modified_time: TIMESTAMP
owners: JSONB  -- array of owner emails
parents: JSONB  -- array of parent folder IDs
indexed_at: TIMESTAMP
is_deleted: BOOLEAN
```

**Table: chunks**
```sql
chunk_id: UUID (PK)
file_id: VARCHAR(255) (FK -> documents.file_id)
chunk_index: INTEGER
chunk_text: TEXT
embedding: VECTOR(1536)  -- pgvector type
parent_heading: VARCHAR(512)
created_at: TIMESTAMP
```

**Table: index_jobs**
```sql
job_id: UUID (PK)
source_id: UUID (FK -> sources.id)
status: VARCHAR(50)  -- 'pending', 'running', 'completed', 'failed'
started_at: TIMESTAMP
completed_at: TIMESTAMP
error_message: TEXT
stats: JSONB  -- docs processed, chunks created, etc.
```

### 6.2 Indexes
- `chunks.embedding` using ivfflat or hnsw (pgvector)
- `chunks.file_id` for efficient document retrieval
- `documents.modified_time` for change queries
- `documents.source_id` for filtering

---

## 7. API Specifications

### 7.1 Retrieval API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/search` | Semantic search |
| GET | `/api/v1/documents/{file_id}` | Get document by ID |
| GET | `/api/v1/changes` | List recent changes |
| POST | `/api/v1/reindex` | Trigger reindex (admin) |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### 7.2 MCP Server Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/mcp` | MCP tool invocation (SSE transport) |
| GET | `/mcp/tools` | List available tools |

---

## 8. Security & Access Control

### 8.1 Authentication Flow
1. Service Account credentials loaded from environment (`GOOGLE_SERVICE_ACCOUNT_JSON`)
2. Domain-wide delegation scope: `https://www.googleapis.com/auth/drive.readonly`
3. Service Account impersonates admin user for Drive API access

### 8.2 MCP Access Control
- API key authentication for MCP clients
- Admin-only tools (reindex_source) require elevated permissions
- Rate limiting per client (100 requests/minute)

### 8.3 Data Access
- No user-level ACL enforcement in v1 (assumes trusted agents)
- All indexed content treated as organization-accessible
- Future: Add per-user Drive permission checks during retrieval

---

## 9. Deployment Architecture

### 9.1 Components
1. **Indexer Service** (containerized Python app)
   - Orchestrated by Prefect/Airflow
   - Runs on schedule or triggered via API
   - Scales horizontally for large corpora

2. **Retrieval API** (containerized FastAPI app)
   - Stateless, horizontally scalable
   - Connects to Postgres via connection pool
   - Exposed via load balancer

3. **MCP Server** (containerized FastAPI app)
   - Thin adapter over Retrieval API
   - SSE transport for tool calls
   - Can be same container as Retrieval API

4. **Postgres Database** (managed service or StatefulSet)
   - pgvector extension installed
   - Regular backups (WAL archiving)
   - Read replicas for query scaling (future)

### 9.2 Environment Variables
```
GOOGLE_SERVICE_ACCOUNT_JSON=<path or JSON string>
DATABASE_URL=postgresql://user:pass@host:5432/dbname
OPENAI_API_KEY=<key>
EMBEDDING_MODEL=text-embedding-3-small
CHUNK_SIZE=600
CHUNK_OVERLAP=100
LOG_LEVEL=INFO
MCP_API_KEY=<secret>
```

---

## 10. Success Metrics

### 10.1 Launch Criteria
- Successfully index ≥10,000 documents from production Google Drive
- Search precision@10 ≥70% (human evaluation on sample queries)
- p95 search latency <1s
- Zero data loss during incremental updates over 1 week
- MCP integration tested with Claude Desktop

### 10.2 Ongoing KPIs
- Index freshness: median lag <30 minutes
- Search success rate: ≥95% of queries return relevant results
- System uptime: ≥99.5%
- Cost per 1M tokens embedded: <$0.05

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Google API rate limits | High | Implement exponential backoff, request batching, quota monitoring |
| Embedding API downtime | Medium | Cache embeddings, graceful degradation, fallback model |
| Large documents exceed memory | Medium | Stream processing, chunk-level processing |
| Stale index data | Medium | Aggressive change polling, manual reindex capability |
| MCP protocol changes | Low | Version pinning, MCP SDK abstraction layer |

---

## 12. Future Enhancements (Post-v1)

- Multi-tenant support with per-organization indexes
- User-level ACL enforcement (check Drive permissions at query time)
- Support for additional sources (Confluence, Notion, SharePoint)
- Advanced chunking strategies (semantic sectioning, entity-aware)
- Hybrid retrieval with BM25 + vector search
- Query analytics and search improvement loop
- Real-time indexing via Drive push notifications (webhooks)
- Support for other embedding models (Cohere, Vertex AI)

---

## 13. Assumptions & Constraints

### 13.1 Assumptions
- Google Workspace domain allows service account delegation
- Network connectivity to Google APIs and OpenAI APIs
- Sufficient quota for Google Drive API (10,000 queries/100s per user)
- Documents primarily in English (embedding model optimized for EN)
- Organization has <1M documents total

### 13.2 Constraints
- Single organization/tenant in v1
- Read-only access to Drive (no write operations)
- No support for real-time document collaboration features
- MCP server requires network connectivity (no offline mode)

---

## 14. Glossary

- **RAG**: Retrieval-Augmented Generation
- **MCP**: Model Context Protocol
- **pgvector**: Postgres extension for vector similarity search
- **SSE**: Server-Sent Events (HTTP streaming)
- **Service Account**: Google Cloud identity for server-to-server auth
- **Domain-Wide Delegation**: Allows service account to impersonate domain users
- **Chunk**: Fixed-size text segment with overlap for retrieval
- **Embedding**: Numerical vector representation of text for semantic similarity

---

## Appendix A: Example Queries

**Query 1**: "What is our company's remote work policy?"
- Expected: Retrieve chunks from HR policy documents
- Citation: Link to specific Google Doc section

**Query 2**: "Show me all Q4 2024 marketing reports"
- Expected: Filter by date range and folder/source
- Citation: Links to all matching documents

**Query 3**: "How do we handle customer data privacy?"
- Expected: Retrieve compliance and legal documents
- Citation: Multiple sources with relevant sections highlighted

---

## Appendix B: Configuration Example

```yaml
# sources.yaml
sources:
  - id: hr-documents
    type: folder
    folder_id: "1A2B3C4D5E6F"
    include_patterns:
      - "*.gdoc"
      - "*.pdf"
    exclude_patterns:
      - "*draft*"
    mime_types:
      - application/vnd.google-apps.document
      - application/pdf
    update_frequency: "*/15 * * * *"  # every 15 min
    
  - id: engineering-shared-drive
    type: shared_drive
    drive_id: "0ABC123XYZ"
    include_patterns:
      - "docs/**"
    mime_types:
      - application/vnd.google-apps.document
    update_frequency: "0 * * * *"  # hourly
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-12-29  
**Status**: Draft for Review
