"""Reindex source MCP tool."""

import logging
from typing import Any

import httpx

from gdrive_rag.config import settings

logger = logging.getLogger(__name__)


async def execute(tool_input: dict[str, Any]) -> dict[str, Any]:
    source_id = tool_input.get("source_id")
    full_reindex = tool_input.get("full_reindex", False)

    if not source_id:
        raise ValueError("source_id is required")

    api_url = f"http://localhost:{settings.api_port}/api/v1/reindex"

    headers = {}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    payload = {
        "source_id": source_id,
        "full_reindex": full_reindex,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    logger.info(f"Reindex job created: {data['job_id']}")
    return data
