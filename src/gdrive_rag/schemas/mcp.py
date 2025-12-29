"""MCP tool input and output schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
