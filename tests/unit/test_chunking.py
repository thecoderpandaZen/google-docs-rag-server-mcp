"""Tests for chunking service."""

from gdrive_rag.services.chunking import ChunkingService


def test_chunk_plain_text():
    service = ChunkingService(target_size=100, overlap=20)
    text = "This is a test. " * 50
    chunks = service.chunk_text(text)

    assert len(chunks) > 0
    assert all(hasattr(chunk, "text") for chunk in chunks)
    assert all(hasattr(chunk, "index") for chunk in chunks)


def test_chunk_html_with_headings():
    service = ChunkingService(target_size=100, overlap=20)
    html = """
    <h1>Main Title</h1>
    <p>First paragraph with some content.</p>
    <h2>Subtitle</h2>
    <p>Second paragraph with more content.</p>
    <p>Third paragraph with even more content to make it longer.</p>
    """

    chunks = service.chunk_html(html)

    assert len(chunks) > 0
    assert chunks[0].parent_heading == "Main Title"


def test_chunk_small_text():
    service = ChunkingService(target_size=100, overlap=20)
    text = "Short text."
    chunks = service.chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0].text == text.strip()


def test_chunk_empty_text():
    service = ChunkingService(target_size=100, overlap=20)
    chunks = service.chunk_text("")

    assert len(chunks) == 0
