#!/usr/bin/env python3
"""
MCP server for converting DOIs to BibTeX format.
HTTP/SSE version for Railway deployment with authentication.
"""

import asyncio
import httpx
import json
import os
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# For HTTP/SSE we need these
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn
from sse_starlette import EventSourceResponse

server = Server("doi-to-bibtex")

# Optional authentication token from environment
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="doi_to_bibtex",
            description="Convert a DOI to BibTeX format. Accepts DOIs in various formats like '10.1234/example', 'doi:10.1234/example', or full URLs like 'https://doi.org/10.1234/example'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doi": {
                        "type": "string",
                        "description": "The DOI to convert. Can be just the DOI (e.g., '10.1234/example'), with 'doi:' prefix, or a full URL.",
                    }
                },
                "required": ["doi"],
            },
        )
    ]

def normalize_doi(doi: str) -> str:
    """Normalize DOI input to just the identifier."""
    doi = doi.strip()
    
    # Remove URL prefix if present
    if doi.startswith("https://doi.org/"):
        doi = doi[16:]
    elif doi.startswith("http://doi.org/"):
        doi = doi[15:]
    elif doi.startswith("https://dx.doi.org/"):
        doi = doi[19:]
    elif doi.startswith("http://dx.doi.org/"):
        doi = doi[18:]
    
    # Remove 'doi:' prefix if present
    if doi.lower().startswith("doi:"):
        doi = doi[4:]
    
    return doi.strip()

async def fetch_bibtex(doi: str) -> str:
    """Fetch BibTeX entry for a DOI using content negotiation."""
    doi = normalize_doi(doi)
    url = f"https://doi.org/{doi}"
    
    headers = {
        "Accept": "application/x-bibtex"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"DOI not found: {doi}")
            elif e.response.status_code == 406:
                raise ValueError(f"BibTeX format not available for DOI: {doi}")
            else:
                raise ValueError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise ValueError(f"Failed to fetch BibTeX: {str(e)}")

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[TextContent]:
    """Handle tool execution requests."""
    if name != "doi_to_bibtex":
        raise ValueError(f"Unknown tool: {name}")
    
    if not arguments or "doi" not in arguments:
        raise ValueError("Missing required argument: doi")
    
    doi = arguments["doi"]
    
    try:
        bibtex = await fetch_bibtex(doi)
        return [
            TextContent(
                type="text",
                text=bibtex
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]

def check_auth(request: Request) -> bool:
    """Check authentication if AUTH_TOKEN is set."""
    if not AUTH_TOKEN:
        return True  # No auth required if not set
    
    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return token == AUTH_TOKEN
    
    return False

# Simple HTTP endpoints
async def handle_health(request: Request):
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "service": "doi-to-bibtex"})

async def handle_sse(request: Request):
    """SSE endpoint for MCP protocol."""
    if not check_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    async def event_generator():
        # Send initial connection event
        yield {
            "event": "endpoint",
            "data": json.dumps({"type": "endpoint", "url": "/message"})
        }
        
        # Keep connection alive
        while True:
            await asyncio.sleep(30)
            yield {"event": "ping", "data": ""}
    
    return EventSourceResponse(event_generator())

async def handle_message(request: Request):
    """Handle MCP messages."""
    if not check_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    try:
        data = await request.json()
        
        # Simple routing based on method
        method = data.get("method", "")
        
        if method == "tools/list":
            tools = await handle_list_tools()
            tools_data = [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema
                }
                for t in tools
            ]
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "result": {"tools": tools_data}
            })
        
        elif method == "tools/call":
            params = data.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            
            result = await handle_call_tool(name, arguments)
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "result": {
                    "content": [
                        {"type": r.type, "text": r.text}
                        for r in result
                    ]
                }
            })
        
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })
    
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": data.get("id", None),
            "error": {"code": -32603, "message": str(e)}
        }, status_code=500)

# Create Starlette app with CORS
app = Starlette(
    debug=True,
    routes=[
        Route("/", endpoint=handle_health),
        Route("/health", endpoint=handle_health),
        Route("/sse", endpoint=handle_sse),
        Route("/message", endpoint=handle_message, methods=["POST"]),
    ],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    if AUTH_TOKEN:
        print(f"✓ Authentication enabled")
    else:
        print("⚠ No AUTH_TOKEN set - authentication disabled (not recommended for production)")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
