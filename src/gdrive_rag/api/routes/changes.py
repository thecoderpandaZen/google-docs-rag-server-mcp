"""Changes tracking endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gdrive_rag.api.deps import get_session, verify_api_key
from gdrive_rag.models import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["changes"])


class ChangeEntry(BaseModel):
    file_id: str
    file_name: str
    modified_time: datetime
    indexed_at: datetime
    is_deleted: bool


class ChangesResponse(BaseModel):
    changes: list[ChangeEntry]
    total: int


@router.get(
    "/changes",
    response_model=ChangesResponse,
    dependencies=[Depends(verify_api_key)],
)
async def list_changes(
    since: datetime = Query(..., description="Return changes since this timestamp"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> ChangesResponse:
    try:
        stmt = (
            select(Document)
            .where(Document.indexed_at >= since)
            .order_by(Document.indexed_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(stmt)
        documents = result.scalars().all()

        changes = [
            ChangeEntry(
                file_id=doc.file_id,
                file_name=doc.file_name,
                modified_time=doc.modified_time,
                indexed_at=doc.indexed_at,
                is_deleted=doc.is_deleted,
            )
            for doc in documents
        ]

        return ChangesResponse(changes=changes, total=len(changes))

    except Exception as e:
        logger.error(f"Error listing changes: {e}")
        raise HTTPException(status_code=500, detail="Failed to list changes")
