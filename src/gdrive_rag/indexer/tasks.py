"""Prefect tasks for indexing workflow."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from prefect import task
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from gdrive_rag.indexer.extractors.docx import DOCXExtractor
from gdrive_rag.indexer.extractors.gdoc import GoogleDocsExtractor
from gdrive_rag.indexer.extractors.pdf import PDFExtractor
from gdrive_rag.models import Chunk, Document
from gdrive_rag.services.chunking import ChunkingService
from gdrive_rag.services.embedding import EmbeddingService
from gdrive_rag.services.google_drive import GoogleDriveService

logger = logging.getLogger(__name__)


@task(retries=3, retry_delay_seconds=60)
def enumerate_files(
    drive_service: GoogleDriveService,
    folder_id: Optional[str] = None,
    mime_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    all_files: List[Dict[str, Any]] = []
    page_token = None

    while True:
        result = drive_service.list_files(
            folder_id=folder_id,
            mime_types=mime_types,
            page_token=page_token,
        )

        files = result.get("files", [])
        all_files.extend(files)

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    logger.info(f"Enumerated {len(all_files)} files")
    return all_files


@task(retries=3, retry_delay_seconds=60)
def extract_content(
    drive_service: GoogleDriveService,
    file_id: str,
    mime_type: str,
) -> Optional[str]:
    try:
        if mime_type == "application/vnd.google-apps.document":
            extractor = GoogleDocsExtractor(drive_service)
        elif mime_type == "application/pdf":
            extractor = PDFExtractor(drive_service)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            extractor = DOCXExtractor(drive_service)
        else:
            logger.warning(f"Unsupported MIME type: {mime_type}")
            return None

        content = extractor.extract(file_id, mime_type)
        return content

    except Exception as e:
        logger.error(f"Error extracting content from {file_id}: {e}")
        return None


@task(retries=2, retry_delay_seconds=30)
def chunk_document(
    content: str,
    is_html: bool = False,
) -> List[Dict[str, Any]]:
    chunking_service = ChunkingService()

    if is_html:
        chunks = chunking_service.chunk_html(content)
    else:
        chunks = chunking_service.chunk_text(content)

    chunk_dicts = [
        {
            "text": chunk.text,
            "index": chunk.index,
            "parent_heading": chunk.parent_heading,
        }
        for chunk in chunks
    ]

    logger.info(f"Created {len(chunk_dicts)} chunks")
    return chunk_dicts


@task(retries=3, retry_delay_seconds=60)
def generate_embeddings(texts: List[str]) -> List[List[float]]:
    embedding_service = EmbeddingService()
    embeddings = embedding_service.embed_texts(texts)

    logger.info(f"Generated {len(embeddings)} embeddings")
    return embeddings


@task(retries=2, retry_delay_seconds=30)
async def upsert_chunks(
    session: AsyncSession,
    file_id: str,
    source_id: str,
    file_metadata: Dict[str, Any],
    chunks_data: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    try:
        await session.execute(delete(Chunk).where(Chunk.file_id == file_id))

        document = await session.get(Document, file_id)
        if not document:
            document = Document(
                file_id=file_id,
                source_id=source_id,
                file_name=file_metadata["name"],
                mime_type=file_metadata["mimeType"],
                web_view_link=file_metadata["webViewLink"],
                modified_time=datetime.fromisoformat(
                    file_metadata["modifiedTime"].replace("Z", "+00:00")
                ),
                owners=file_metadata.get("owners", []),
                parents=file_metadata.get("parents", []),
                indexed_at=datetime.utcnow(),
                is_deleted=False,
            )
            session.add(document)
        else:
            document.file_name = file_metadata["name"]
            document.mime_type = file_metadata["mimeType"]
            document.web_view_link = file_metadata["webViewLink"]
            document.modified_time = datetime.fromisoformat(
                file_metadata["modifiedTime"].replace("Z", "+00:00")
            )
            document.indexed_at = datetime.utcnow()
            document.is_deleted = False

        for chunk_data, embedding in zip(chunks_data, embeddings):
            chunk = Chunk(
                file_id=file_id,
                chunk_index=chunk_data["index"],
                chunk_text=chunk_data["text"],
                embedding=embedding,
                parent_heading=chunk_data.get("parent_heading"),
                created_at=datetime.utcnow(),
            )
            session.add(chunk)

        await session.commit()

        logger.info(f"Upserted {len(chunks_data)} chunks for file {file_id}")
        return len(chunks_data)

    except Exception as e:
        await session.rollback()
        logger.error(f"Error upserting chunks for {file_id}: {e}")
        raise
