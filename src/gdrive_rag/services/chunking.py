"""Structure-aware text chunking service."""

import logging
import re

from bs4 import BeautifulSoup

from gdrive_rag.config import settings

logger = logging.getLogger(__name__)


class ChunkResult:
    def __init__(
        self,
        text: str,
        index: int,
        parent_heading: str | None = None,
    ) -> None:
        self.text = text
        self.index = index
        self.parent_heading = parent_heading


class ChunkingService:
    def __init__(
        self,
        target_size: int = settings.chunk_target_size,
        overlap: int = settings.chunk_overlap,
    ) -> None:
        self.target_size = target_size
        self.overlap = overlap

    def chunk_html(self, html_content: str) -> list[ChunkResult]:
        soup = BeautifulSoup(html_content, "html.parser")
        return self._chunk_document(soup)

    def chunk_text(self, text_content: str) -> list[ChunkResult]:
        return self._chunk_plain_text(text_content)

    def _chunk_document(self, soup: BeautifulSoup) -> list[ChunkResult]:
        chunks: list[ChunkResult] = []
        current_heading = None
        current_text_parts: list[str] = []
        chunk_index = 0

        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                if current_text_parts:
                    new_chunks = self._create_chunks_from_text(
                        " ".join(current_text_parts),
                        chunk_index,
                        current_heading,
                    )
                    chunks.extend(new_chunks)
                    chunk_index += len(new_chunks)
                    current_text_parts = []

                current_heading = element.get_text(strip=True)

            elif element.name == "p":
                text = element.get_text(strip=True)
                if text:
                    current_text_parts.append(text)

                    current_length = sum(len(p) for p in current_text_parts)
                    if current_length >= self.target_size:
                        new_chunks = self._create_chunks_from_text(
                            " ".join(current_text_parts),
                            chunk_index,
                            current_heading,
                        )
                        chunks.extend(new_chunks)
                        chunk_index += len(new_chunks)
                        current_text_parts = []

        if current_text_parts:
            new_chunks = self._create_chunks_from_text(
                " ".join(current_text_parts),
                chunk_index,
                current_heading,
            )
            chunks.extend(new_chunks)

        return chunks

    def _chunk_plain_text(self, text: str) -> list[ChunkResult]:
        chunks: list[ChunkResult] = []
        chunk_index = 0

        paragraphs = text.split("\n\n")
        current_text_parts: list[str] = []

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            current_text_parts.append(paragraph)
            current_length = sum(len(p) for p in current_text_parts)

            if current_length >= self.target_size:
                new_chunks = self._create_chunks_from_text(
                    " ".join(current_text_parts),
                    chunk_index,
                    None,
                )
                chunks.extend(new_chunks)
                chunk_index += len(new_chunks)
                current_text_parts = []

        if current_text_parts:
            new_chunks = self._create_chunks_from_text(
                " ".join(current_text_parts),
                chunk_index,
                None,
            )
            chunks.extend(new_chunks)

        return chunks

    def _create_chunks_from_text(
        self,
        text: str,
        start_index: int,
        parent_heading: str | None,
    ) -> list[ChunkResult]:
        if len(text) <= self.target_size:
            return [ChunkResult(text, start_index, parent_heading)]

        chunks: list[ChunkResult] = []
        sentences = self._split_sentences(text)

        current_chunk: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > self.target_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(ChunkResult(chunk_text, start_index + len(chunks), parent_heading))

                overlap_text = (
                    chunk_text[-self.overlap :] if len(chunk_text) > self.overlap else chunk_text
                )
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text)

            current_chunk.append(sentence)
            current_length += sentence_length + 1

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(ChunkResult(chunk_text, start_index + len(chunks), parent_heading))

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
