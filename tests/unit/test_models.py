"""Tests for database models."""

import uuid
from datetime import datetime

from gdrive_rag.models import Chunk, Document, IndexJob, Source


async def test_source_model(db_session):
    source = Source(
        id=uuid.uuid4(),
        name="Test Source",
        type="folder",
        config={"folder_id": "test123"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)

    assert source.name == "Test Source"
    assert source.type == "folder"
    assert source.config["folder_id"] == "test123"


async def test_document_model(db_session):
    source = Source(
        id=uuid.uuid4(),
        name="Test Source",
        type="folder",
        config={"folder_id": "test123"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(source)
    await db_session.commit()

    document = Document(
        file_id="doc123",
        source_id=source.id,
        file_name="Test Document",
        mime_type="application/vnd.google-apps.document",
        web_view_link="https://docs.google.com/document/d/doc123",
        modified_time=datetime.utcnow(),
        owners=[],
        parents=[],
        indexed_at=datetime.utcnow(),
        is_deleted=False,
    )

    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    assert document.file_id == "doc123"
    assert document.file_name == "Test Document"
    assert document.is_deleted is False


async def test_chunk_model(db_session):
    source = Source(
        id=uuid.uuid4(),
        name="Test Source",
        type="folder",
        config={"folder_id": "test123"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(source)
    await db_session.commit()

    document = Document(
        file_id="doc456",
        source_id=source.id,
        file_name="Test Document",
        mime_type="application/vnd.google-apps.document",
        web_view_link="https://docs.google.com/document/d/doc456",
        modified_time=datetime.utcnow(),
        owners=[],
        parents=[],
        indexed_at=datetime.utcnow(),
        is_deleted=False,
    )
    db_session.add(document)
    await db_session.commit()

    embedding = [0.1] * 1536
    chunk = Chunk(
        chunk_id=uuid.uuid4(),
        file_id=document.file_id,
        chunk_index=0,
        chunk_text="This is a test chunk",
        embedding=embedding,
        parent_heading="Test Heading",
        created_at=datetime.utcnow(),
    )

    db_session.add(chunk)
    await db_session.commit()
    await db_session.refresh(chunk)

    assert chunk.chunk_text == "This is a test chunk"
    assert chunk.chunk_index == 0
    assert chunk.parent_heading == "Test Heading"
    assert len(chunk.embedding) == 1536


async def test_index_job_model(db_session):
    source = Source(
        id=uuid.uuid4(),
        name="Test Source",
        type="folder",
        config={"folder_id": "test123"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(source)
    await db_session.commit()

    job = IndexJob(
        job_id=uuid.uuid4(),
        source_id=source.id,
        status="completed",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        stats={"files_processed": 10, "chunks_created": 100},
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    assert job.status == "completed"
    assert job.stats["files_processed"] == 10
    assert job.stats["chunks_created"] == 100
