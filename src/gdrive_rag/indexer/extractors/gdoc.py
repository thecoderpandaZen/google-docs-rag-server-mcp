"""Google Docs text extractor."""

import logging

from bs4 import BeautifulSoup

from gdrive_rag.indexer.extractors.base import Extractor
from gdrive_rag.services.google_drive import GoogleDriveService

logger = logging.getLogger(__name__)


class GoogleDocsExtractor(Extractor):
    def __init__(self, drive_service: GoogleDriveService) -> None:
        self.drive_service = drive_service

    def extract(self, file_id: str, mime_type: str) -> str | None:
        try:
            html_content = self.drive_service.get_file_content(file_id, mime_type)

            if not html_content:
                logger.warning(f"Empty content for Google Doc {file_id}")
                return None

            soup = BeautifulSoup(html_content, "html.parser")

            text_content = soup.get_text(separator="\n", strip=True)

            if not text_content.strip():
                logger.warning(f"No text content extracted from {file_id}")
                return None

            return text_content

        except Exception as e:
            logger.error(f"Error extracting Google Doc {file_id}: {e}")
            return None
