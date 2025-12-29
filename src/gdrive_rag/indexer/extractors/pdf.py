"""PDF text extractor."""

import logging
from io import BytesIO

from PyPDF2 import PdfReader

from gdrive_rag.indexer.extractors.base import Extractor
from gdrive_rag.services.google_drive import GoogleDriveService

logger = logging.getLogger(__name__)


class PDFExtractor(Extractor):
    def __init__(self, drive_service: GoogleDriveService) -> None:
        self.drive_service = drive_service

    def extract(self, file_id: str, mime_type: str) -> str | None:
        try:
            pdf_bytes = self.drive_service.get_file_content(file_id, mime_type)

            if not pdf_bytes:
                logger.warning(f"Empty content for PDF {file_id}")
                return None

            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)

            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                logger.warning(f"No text content extracted from PDF {file_id}")
                return None

            return full_text

        except Exception as e:
            logger.error(f"Error extracting PDF {file_id}: {e}")
            return None
