"""Search documents MCP tool."""

import logging
from typing import Any

import httpx

from gdrive_rag.config import settings

logger = logging.getLogger(__name__)


async def execute(tool_input: dict[str, Any]) -> dict[str, Any]:
    query = tool_input.get("query")
    max_results = tool_input.get("max_results", 10)

    if not query:
        raise ValueError("query is required")

    api_url = f"http://localhost:{settings.api_port}/api/v1/search"

    headers = {}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    payload = {
        "query": query,
        "top_k": max_results,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    logger.info(f"Search returned {data['total']} results")
    return data
