"""Pydantic schemas for API validation."""

from gdrive_rag.schemas.document import ChunkMetadata, DocumentMetadata, DocumentResponse
from gdrive_rag.schemas.mcp import (
    MCPGetDocumentInput,
    MCPListChangesInput,
    MCPReindexSourceInput,
    MCPSearchDocsInput,
)
from gdrive_rag.schemas.search import SearchFilters, SearchRequest, SearchResponse, SearchResult

__all__ = [
    "SearchFilters",
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
    "ChunkMetadata",
    "DocumentMetadata",
    "DocumentResponse",
    "MCPSearchDocsInput",
    "MCPGetDocumentInput",
    "MCPListChangesInput",
    "MCPReindexSourceInput",
]
