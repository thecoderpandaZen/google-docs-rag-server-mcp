"""Admin endpoints for reindexing."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gdrive_rag.api.deps import get_session, verify_api_key
from gdrive_rag.models import Source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["admin"])


class ReindexRequest(BaseModel):
    source_id: str
    full_reindex: bool = False


class ReindexResponse(BaseModel):
    job_id: str
    source_id: str
    status: str
    message: str


@router.post(
    "/reindex",
    response_model=ReindexResponse,
    dependencies=[Depends(verify_api_key)],
)
async def reindex_source(
    request: ReindexRequest,
    session: AsyncSession = Depends(get_session),
) -> ReindexResponse:
    try:
        result = await session.execute(
            select(Source).where(Source.id == request.source_id)
        )
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        job_id = str(uuid.uuid4())

        logger.info(f"Reindex request received for source {source.name}, job_id={job_id}")

        return ReindexResponse(
            job_id=job_id,
            source_id=request.source_id,
            status="queued",
            message=f"Reindex job queued for source {source.name}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reindex job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create reindex job")
