"""MCP Server implementation."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from gdrive_rag.config import settings
from gdrive_rag.mcp.tools import get_document, list_changes, reindex_source, search_docs

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Google Drive RAG MCP Server",
    description="MCP server for Google Drive RAG",
    version="0.1.0",
)

security = HTTPBearer(auto_error=False)


async def verify_mcp_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> None:
    if not settings.mcp_auth_token:
        return

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication")

    if credentials.credentials != settings.mcp_auth_token:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/mcp/tools")
async def list_tools() -> dict[str, Any]:
    tools = [
        {
            "name": "search_docs",
            "description": "Search for documents in Google Drive using semantic search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_document",
            "description": "Get a specific document by file ID with all chunks",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "Google Drive file ID"},
                },
                "required": ["file_id"],
            },
        },
        {
            "name": "list_recent_changes",
            "description": "List recently changed or indexed documents",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "since": {
                        "type": "string",
                        "format": "date-time",
                        "description": "ISO timestamp to list changes since",
                    },
                },
                "required": ["since"],
            },
        },
        {
            "name": "reindex_source",
            "description": "Trigger reindexing of a source (admin only)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "description": "Source UUID"},
                    "full_reindex": {
                        "type": "boolean",
                        "description": "Full reindex vs incremental",
                        "default": False,
                    },
                },
                "required": ["source_id"],
            },
        },
    ]

    return {"tools": tools}


@app.post("/mcp/call/{tool_name}")
async def call_tool(
    tool_name: str,
    request: Request,
) -> dict[str, Any]:
    try:
        body = await request.json()
        tool_input = body.get("input", {})

        if tool_name == "search_docs":
            result = await search_docs.execute(tool_input)
        elif tool_name == "get_document":
            result = await get_document.execute(tool_input)
        elif tool_name == "list_recent_changes":
            result = await list_changes.execute(tool_input)
        elif tool_name == "reindex_source":
            result = await reindex_source.execute(tool_input)
        else:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

        return {"result": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting MCP Server on port %d", settings.mcp_port)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down MCP Server")
