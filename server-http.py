#!/usr/bin/env python3
"""
MCP server for converting DOIs to BibTeX format.
HTTP/SSE version for Railway deployment.
"""

import asyncio
import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
import uvicorn
import os

server = Server("doi-to-bibtex")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
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
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    if name != "doi_to_bibtex":
        raise ValueError(f"Unknown tool: {name}")
    
    if not arguments or "doi" not in arguments:
        raise ValueError("Missing required argument: doi")
    
    doi = arguments["doi"]
    
    try:
        bibtex = await fetch_bibtex(doi)
        return [
            types.TextContent(
                type="text",
                text=bibtex
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]

async def handle_sse(request):
    """Handle SSE connection."""
    async with SseServerTransport("/messages") as transport:
        await server.run(
            transport.read_stream,
            transport.write_stream,
            InitializationOptions(
                server_name="doi-to-bibtex",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
    return Response()

async def handle_messages(request):
    """Handle message endpoint."""
    return Response()

app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
