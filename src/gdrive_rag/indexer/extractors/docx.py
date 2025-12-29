"""DOCX text extractor."""

import logging
from io import BytesIO
from typing import Optional

from docx import Document

from gdrive_rag.indexer.extractors.base import Extractor
from gdrive_rag.services.google_drive import GoogleDriveService

logger = logging.getLogger(__name__)


class DOCXExtractor(Extractor):
    def __init__(self, drive_service: GoogleDriveService) -> None:
        self.drive_service = drive_service

    def extract(self, file_id: str, mime_type: str) -> Optional[str]:
        try:
            docx_bytes = self.drive_service.get_file_content(file_id, mime_type)

            if not docx_bytes:
                logger.warning(f"Empty content for DOCX {file_id}")
                return None

            docx_file = BytesIO(docx_bytes)
            doc = Document(docx_file)

            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                logger.warning(f"No text content extracted from DOCX {file_id}")
                return None

            return full_text

        except Exception as e:
            logger.error(f"Error extracting DOCX {file_id}: {e}")
            return None
