"""Search endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from gdrive_rag.api.deps import get_session, verify_api_key
from gdrive_rag.schemas.search import SearchRequest, SearchResponse
from gdrive_rag.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse, dependencies=[Depends(verify_api_key)])
async def search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    try:
        retrieval_service = RetrievalService(session)
        results = await retrieval_service.search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
        )

        return SearchResponse(
            results=results,
            query=request.query,
            total=len(results),
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")
