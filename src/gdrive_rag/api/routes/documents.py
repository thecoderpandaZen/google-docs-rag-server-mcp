"""Document retrieval endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gdrive_rag.api.deps import get_session, verify_api_key
from gdrive_rag.models import Document
from gdrive_rag.schemas.document import ChunkMetadata, DocumentMetadata, DocumentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get(
    "/documents/{file_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_document(
    file_id: str,
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    try:
        result = await session.execute(
            select(Document)
            .where(Document.file_id == file_id)
            .options(selectinload(Document.chunks))
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        metadata = DocumentMetadata(
            file_id=document.file_id,
            file_name=document.file_name,
            mime_type=document.mime_type,
            web_view_link=document.web_view_link,
            modified_time=document.modified_time,
            indexed_at=document.indexed_at,
            is_deleted=document.is_deleted,
        )

        chunks = [
            ChunkMetadata(
                chunk_id=str(chunk.chunk_id),
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                parent_heading=chunk.parent_heading,
                created_at=chunk.created_at,
            )
            for chunk in sorted(document.chunks, key=lambda c: c.chunk_index)
        ]

        return DocumentResponse(metadata=metadata, chunks=chunks)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")
