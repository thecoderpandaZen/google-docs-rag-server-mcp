"""Hybrid retrieval service with vector search."""

import logging

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from gdrive_rag.models import Chunk, Document
from gdrive_rag.schemas.search import SearchFilters, SearchResult
from gdrive_rag.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.embedding_service = EmbeddingService()

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        query_embedding = self.embedding_service.embed_text(query)

        stmt = (
            select(
                Chunk.chunk_id,
                Chunk.file_id,
                Chunk.chunk_text,
                Chunk.chunk_index,
                Chunk.parent_heading,
                Document.file_name,
                Document.web_view_link,
                Document.modified_time,
                (1 - Chunk.embedding.cosine_distance(query_embedding)).label("score"),
            )
            .join(Document, Chunk.file_id == Document.file_id)
            .where(Document.is_deleted == False)
        )

        if filters:
            if filters.source_ids:
                stmt = stmt.where(Document.source_id.in_(filters.source_ids))
            if filters.mime_types:
                stmt = stmt.where(Document.mime_type.in_(filters.mime_types))
            if filters.modified_after:
                stmt = stmt.where(Document.modified_time >= filters.modified_after)

        stmt = stmt.order_by(desc("score")).limit(top_k)

        result = await self.session.execute(stmt)
        rows = result.all()

        search_results = [
            SearchResult(
                chunk_id=str(row.chunk_id),
                file_id=row.file_id,
                file_name=row.file_name,
                chunk_text=row.chunk_text,
                chunk_index=row.chunk_index,
                score=float(row.score),
                web_view_link=row.web_view_link,
                modified_time=row.modified_time,
            )
            for row in rows
        ]

        logger.info(f"Found {len(search_results)} results for query")
        return search_results
