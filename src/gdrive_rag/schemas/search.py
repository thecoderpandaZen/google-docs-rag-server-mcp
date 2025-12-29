"""Search request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    source_ids: list[str] | None = None
    mime_types: list[str] | None = None
    modified_after: datetime | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: SearchFilters | None = None


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
    results: list[SearchResult]
    query: str
    total: int
