"""Tests for embedding service."""

from unittest.mock import Mock, patch

from gdrive_rag.services.embedding import EmbeddingService


@patch("gdrive_rag.services.embedding.OpenAI")
def test_embed_text(mock_openai_class):
    mock_client = Mock()
    mock_openai_class.return_value = mock_client

    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create.return_value = mock_response

    service = EmbeddingService()
    embedding = service.embed_text("Test text")

    assert len(embedding) == 1536
    assert embedding[0] == 0.1
    mock_client.embeddings.create.assert_called_once()


@patch("gdrive_rag.services.embedding.OpenAI")
def test_embed_texts_batching(mock_openai_class):
    mock_client = Mock()
    mock_openai_class.return_value = mock_client

    def create_response_mock(*args, **kwargs):
        batch_size = len(kwargs.get("input", []))
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536) for _ in range(batch_size)]
        return mock_response

    mock_client.embeddings.create.side_effect = create_response_mock

    service = EmbeddingService()
    service.batch_size = 10

    texts = ["Text " + str(i) for i in range(25)]
    embeddings = service.embed_texts(texts)

    assert len(embeddings) == 25
    assert all(len(emb) == 1536 for emb in embeddings)
    assert mock_client.embeddings.create.call_count == 3


@patch("gdrive_rag.services.embedding.OpenAI")
def test_embed_empty_list(mock_openai_class):
    mock_client = Mock()
    mock_openai_class.return_value = mock_client

    service = EmbeddingService()
    embeddings = service.embed_texts([])

    assert embeddings == []
    mock_client.embeddings.create.assert_not_called()
