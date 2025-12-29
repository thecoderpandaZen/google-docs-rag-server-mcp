"""Prefect flows for indexing workflows."""

import logging
import uuid
from datetime import datetime
from typing import Any

from prefect import flow
from sqlalchemy import select, update

from gdrive_rag.db.session import async_session_factory
from gdrive_rag.indexer.tasks import (
    chunk_document,
    enumerate_files,
    extract_content,
    generate_embeddings,
    upsert_chunks,
)
from gdrive_rag.models import IndexJob, Source
from gdrive_rag.services.google_drive import GoogleDriveService

logger = logging.getLogger(__name__)

SUPPORTED_MIME_TYPES = [
    "application/vnd.google-apps.document",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]


@flow(name="full-crawl", log_prints=True)
async def full_crawl_flow(source_id: str) -> dict[str, Any]:
    job_id = uuid.uuid4()
    stats: dict[str, Any] = {
        "files_processed": 0,
        "files_failed": 0,
        "chunks_created": 0,
    }

    async with async_session_factory() as session:
        try:
            result = await session.execute(select(Source).where(Source.id == source_id))
            source = result.scalar_one_or_none()

            if not source:
                raise ValueError(f"Source {source_id} not found")

            job = IndexJob(
                job_id=job_id,
                source_id=source.id,
                status="running",
                started_at=datetime.utcnow(),
                stats=stats,
            )
            session.add(job)
            await session.commit()

            logger.info(f"Starting full crawl for source {source.name}")

            drive_service = GoogleDriveService()

            folder_id = source.config.get("folder_id")
            files = enumerate_files(drive_service, folder_id, SUPPORTED_MIME_TYPES)

            for file_metadata in files:
                try:
                    file_id = file_metadata["id"]
                    mime_type = file_metadata["mimeType"]

                    logger.info(f"Processing file {file_metadata['name']} ({file_id})")

                    content = extract_content(drive_service, file_id, mime_type)

                    if not content:
                        logger.warning(f"No content extracted for {file_id}")
                        stats["files_failed"] += 1
                        continue

                    is_html = mime_type == "application/vnd.google-apps.document"
                    chunks_data = chunk_document(content, is_html)

                    if not chunks_data:
                        logger.warning(f"No chunks created for {file_id}")
                        stats["files_failed"] += 1
                        continue

                    chunk_texts = [chunk["text"] for chunk in chunks_data]
                    embeddings = generate_embeddings(chunk_texts)

                    chunks_created = await upsert_chunks(
                        session,
                        file_id,
                        str(source.id),
                        file_metadata,
                        chunks_data,
                        embeddings,
                    )

                    stats["files_processed"] += 1
                    stats["chunks_created"] += chunks_created

                except Exception as e:
                    logger.error(f"Error processing file {file_metadata.get('id')}: {e}")
                    stats["files_failed"] += 1

            await session.execute(
                update(Source)
                .where(Source.id == source.id)
                .values(last_indexed_at=datetime.utcnow())
            )

            await session.execute(
                update(IndexJob)
                .where(IndexJob.job_id == job_id)
                .values(
                    status="completed",
                    completed_at=datetime.utcnow(),
                    stats=stats,
                )
            )
            await session.commit()

            logger.info(f"Full crawl completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Full crawl failed: {e}")

            await session.execute(
                update(IndexJob)
                .where(IndexJob.job_id == job_id)
                .values(
                    status="failed",
                    completed_at=datetime.utcnow(),
                    error_message=str(e),
                    stats=stats,
                )
            )
            await session.commit()

            raise


@flow(name="incremental-update", log_prints=True)
async def incremental_update_flow(source_id: str) -> dict[str, Any]:
    job_id = uuid.uuid4()
    stats: dict[str, Any] = {
        "files_processed": 0,
        "files_failed": 0,
        "chunks_created": 0,
    }

    async with async_session_factory() as session:
        try:
            result = await session.execute(select(Source).where(Source.id == source_id))
            source = result.scalar_one_or_none()

            if not source:
                raise ValueError(f"Source {source_id} not found")

            job = IndexJob(
                job_id=job_id,
                source_id=source.id,
                status="running",
                started_at=datetime.utcnow(),
                stats=stats,
            )
            session.add(job)
            await session.commit()

            logger.info(f"Starting incremental update for source {source.name}")

            drive_service = GoogleDriveService()

            page_token = source.config.get("page_token")
            if not page_token:
                page_token = drive_service.get_start_page_token()

            changes = drive_service.list_changes(page_token)

            for change in changes.get("changes", []):
                try:
                    file_id = change.get("fileId")
                    removed = change.get("removed", False)
                    file_data = change.get("file")

                    if removed or (file_data and file_data.get("trashed")):
                        logger.info(f"Marking file {file_id} as deleted")
                        await session.execute(
                            update(Document)
                            .where(Document.file_id == file_id)
                            .values(is_deleted=True)
                        )
                        stats["files_processed"] += 1
                        continue

                    if not file_data:
                        continue

                    mime_type = file_data.get("mimeType")
                    if mime_type not in SUPPORTED_MIME_TYPES:
                        continue

                    logger.info(f"Processing changed file {file_data['name']} ({file_id})")

                    content = extract_content(drive_service, file_id, mime_type)

                    if not content:
                        logger.warning(f"No content extracted for {file_id}")
                        stats["files_failed"] += 1
                        continue

                    is_html = mime_type == "application/vnd.google-apps.document"
                    chunks_data = chunk_document(content, is_html)

                    chunk_texts = [chunk["text"] for chunk in chunks_data]
                    embeddings = generate_embeddings(chunk_texts)

                    chunks_created = await upsert_chunks(
                        session,
                        file_id,
                        str(source.id),
                        file_data,
                        chunks_data,
                        embeddings,
                    )

                    stats["files_processed"] += 1
                    stats["chunks_created"] += chunks_created

                except Exception as e:
                    logger.error(f"Error processing change: {e}")
                    stats["files_failed"] += 1

            new_page_token = changes.get("newStartPageToken", page_token)
            source.config["page_token"] = new_page_token

            await session.execute(
                update(Source)
                .where(Source.id == source.id)
                .values(
                    last_indexed_at=datetime.utcnow(),
                    config=source.config,
                )
            )

            await session.execute(
                update(IndexJob)
                .where(IndexJob.job_id == job_id)
                .values(
                    status="completed",
                    completed_at=datetime.utcnow(),
                    stats=stats,
                )
            )
            await session.commit()

            logger.info(f"Incremental update completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Incremental update failed: {e}")

            await session.execute(
                update(IndexJob)
                .where(IndexJob.job_id == job_id)
                .values(
                    status="failed",
                    completed_at=datetime.utcnow(),
                    error_message=str(e),
                    stats=stats,
                )
            )
            await session.commit()

            raise
