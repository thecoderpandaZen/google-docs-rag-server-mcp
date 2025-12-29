"""Document schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    chunk_id: str
    chunk_index: int
    chunk_text: str
    parent_heading: Optional[str] = None
    created_at: datetime


class DocumentMetadata(BaseModel):
    file_id: str
    file_name: str
    mime_type: str
    web_view_link: str
    modified_time: datetime
    indexed_at: datetime
    is_deleted: bool


class DocumentResponse(BaseModel):
    metadata: DocumentMetadata
    chunks: List[ChunkMetadata]
