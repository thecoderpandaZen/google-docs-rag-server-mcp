"""Main FastAPI application for Retrieval API."""

import logging

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gdrive_rag.api.deps import get_session
from gdrive_rag.api.routes import admin, changes, documents, search
from gdrive_rag.config import settings
from gdrive_rag.utils.metrics import get_metrics

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Google Drive RAG API",
    description="Retrieval-Augmented Generation API for Google Drive content",
    version="0.1.0",
)

app.include_router(search.router)
app.include_router(documents.router)
app.include_router(changes.router)
app.include_router(admin.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_session)) -> dict:
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.get("/metrics")
async def metrics() -> Response:
    metrics_output = get_metrics()
    return Response(content=metrics_output, media_type="text/plain")


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting Retrieval API on port %d", settings.api_port)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down Retrieval API")
