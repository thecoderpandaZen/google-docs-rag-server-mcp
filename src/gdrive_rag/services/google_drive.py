"""Google Drive API client wrapper."""

import logging
import time
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

from gdrive_rag.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


class GoogleDriveService:
    def __init__(self) -> None:
        self.credentials = self._get_credentials()
        self.drive_service = build("drive", "v3", credentials=self.credentials)
        self.docs_service = build("docs", "v1", credentials=self.credentials)

    def _get_credentials(self) -> service_account.Credentials:
        if not settings.google_service_account_file:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_FILE not configured")

        credentials = service_account.Credentials.from_service_account_file(
            settings.google_service_account_file, scopes=SCOPES
        )

        if settings.google_delegated_user:
            credentials = credentials.with_subject(settings.google_delegated_user)

        return credentials

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def list_files(
        self,
        folder_id: Optional[str] = None,
        mime_types: Optional[List[str]] = None,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        query_parts = []

        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")

        if mime_types:
            mime_conditions = [f"mimeType = '{mt}'" for mt in mime_types]
            query_parts.append(f"({' or '.join(mime_conditions)})")

        query_parts.append("trashed = false")

        query = " and ".join(query_parts)

        try:
            result = (
                self.drive_service.files()
                .list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime, "
                    "webViewLink, owners, parents)",
                    pageToken=page_token,
                )
                .execute()
            )
            return result
        except HttpError as e:
            logger.error(f"Error listing files: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        try:
            file_metadata = (
                self.drive_service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, modifiedTime, webViewLink, owners, parents",
                )
                .execute()
            )
            return file_metadata
        except HttpError as e:
            logger.error(f"Error getting file metadata for {file_id}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def get_file_content(self, file_id: str, mime_type: str) -> bytes:
        try:
            if mime_type == "application/vnd.google-apps.document":
                request = self.drive_service.files().export_media(
                    fileId=file_id, mimeType="text/html"
                )
            else:
                request = self.drive_service.files().get_media(fileId=file_id)

            content = request.execute()
            return content
        except HttpError as e:
            logger.error(f"Error getting file content for {file_id}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def get_document(self, document_id: str) -> Dict[str, Any]:
        try:
            document = self.docs_service.documents().get(documentId=document_id).execute()
            return document
        except HttpError as e:
            logger.error(f"Error getting document {document_id}: {e}")
            raise

    def get_start_page_token(self) -> str:
        try:
            response = self.drive_service.changes().getStartPageToken().execute()
            return response.get("startPageToken")
        except HttpError as e:
            logger.error(f"Error getting start page token: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def list_changes(
        self, page_token: str, page_size: int = 100
    ) -> Dict[str, Any]:
        try:
            response = (
                self.drive_service.changes()
                .list(
                    pageToken=page_token,
                    pageSize=page_size,
                    fields="nextPageToken, newStartPageToken, changes(fileId, removed, "
                    "file(id, name, mimeType, modifiedTime, webViewLink, owners, parents, trashed))",
                )
                .execute()
            )
            return response
        except HttpError as e:
            logger.error(f"Error listing changes: {e}")
            raise
