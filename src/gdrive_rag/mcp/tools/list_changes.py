"""List changes MCP tool."""

import logging
from typing import Any, Dict

import httpx

from gdrive_rag.config import settings

logger = logging.getLogger(__name__)


async def execute(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    since = tool_input.get("since")

    if not since:
        raise ValueError("since timestamp is required")

    api_url = f"http://localhost:{settings.api_port}/api/v1/changes"

    headers = {}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    params = {"since": since}

    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    logger.info(f"Retrieved {data['total']} changes")
    return data
