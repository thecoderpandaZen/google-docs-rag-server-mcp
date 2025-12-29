"""Get document MCP tool."""

import logging
from typing import Any, Dict

import httpx

from gdrive_rag.config import settings

logger = logging.getLogger(__name__)


async def execute(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    file_id = tool_input.get("file_id")

    if not file_id:
        raise ValueError("file_id is required")

    api_url = f"http://localhost:{settings.api_port}/api/v1/documents/{file_id}"

    headers = {}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()

    logger.info(f"Retrieved document {file_id}")
    return data
