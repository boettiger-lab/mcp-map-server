#!/usr/bin/env python3
"""
MCP Map Server - Streamable HTTP (Redis-free)
"""

import asyncio
import json
import uuid
import os
from typing import Any, AsyncIterator
from pathlib import Path
import contextlib

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent

# --- Global In-Memory State ---
sessions = {}

def get_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = {
            "state": {
                "version": 1,
                "center": [-98.5795, 39.8283],
                "zoom": 4,
                "layers": {}
            },
            "queues": []
        }
    return sessions[session_id]

async def notify_session(session_id: str, state: dict):
    if session_id in sessions:
        for queue in sessions[session_id]["queues"]:
            await queue.put(state)

# --- MCP Server ---
server = Server("mcp-map-server-stream")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available map control tools"""
    return [
        Tool(
            name="add_layer",
            description="Add a new map layer",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "id": {"type": "string"},
                    "type": {"type": "string", "enum": ["raster", "vector"]},
                    "source": {"type": "object"},
                    "layers": {"type": "array", "items": {"type": "object"}},
                    "visible": {"type": "boolean"}
                },
                "required": ["session_id", "id", "type", "source"]
            }
        ),
        Tool(
            name="remove_layer",
            description="Remove a layer",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "id": {"type": "string"}
                },
                "required": ["session_id", "id"]
            }
        ),
        Tool(
            name="set_map_view",
            description="Set map center/zoom",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "center": {"type": "array", "items": {"type": "number"}},
                    "zoom": {"type": "number"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="list_layers",
            description="List all layers in a session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="filter_layer",
            description="Apply filter to layer",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "layer_id": {"type": "string"},
                    "filter": {"description": "Filter expression"}
                },
                "required": ["session_id", "layer_id"]
            }
        ),
         Tool(
            name="set_layer_paint",
            description="Set paint properties",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "layer_id": {"type": "string"},
                    "property": {"type": "string"},
                    "value": {"description": "Paint value"}
                },
                "required": ["session_id", "layer_id", "property", "value"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    session_id = arguments.get("session_id")
    if not session_id:
        return [TextContent(type="text", text=json.dumps({"success": False, "error": "session_id required"}))]
    
    session = get_session(session_id)
    state = session["state"]
    
    if name == "add_layer":
        layer_id = arguments["id"]
        layer_type = arguments["type"]
        source = arguments["source"]
        layers = arguments.get("layers", [])
        visible = arguments.get("visible", True)
        
        if layer_type == "raster" and not layers:
            layers = [{"id": layer_id, "type": "raster", "source": layer_id}]
        
        state["layers"][layer_id] = {
            "id": layer_id,
            "type": layer_type,
            "visible": visible,
            "source": source,
            "layers": layers,
            "paint": {},
            "filter": None
        }
        await notify_session(session_id, state)
        return [TextContent(type="text", text=json.dumps({"success": True, "message": f"Added layer {layer_id}"}))]
    
    elif name == "remove_layer":
        layer_id = arguments["id"]
        if layer_id in state["layers"]:
            del state["layers"][layer_id]
            await notify_session(session_id, state)
            return [TextContent(type="text", text=json.dumps({"success": True, "message": f"Removed layer {layer_id}"}))]
        return [TextContent(type="text", text=json.dumps({"success": False, "error": "Layer not found"}))]

    elif name == "set_map_view":
        if "center" in arguments:
            state["center"] = arguments["center"]
        if "zoom" in arguments:
            state["zoom"] = arguments["zoom"]
        await notify_session(session_id, state)
        return [TextContent(type="text", text=json.dumps({"success": True, "center": state["center"]}))]

    elif name == "list_layers":
         return [TextContent(type="text", text=json.dumps({"success": True, "layers": state["layers"]}))]

    elif name == "filter_layer":
        layer_id = arguments["layer_id"]
        # Simplified implementation for prototype
        await notify_session(session_id, state)
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Filter applied (mock)"}))]

    elif name == "set_layer_paint":
        # Simplified mock
        await notify_session(session_id, state)
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Paint set (mock)"}))]

    return [TextContent(type="text", text=json.dumps({"success": False, "error": f"Unknown tool: {name}"}))]


# --- Starlette App & Transport ---

async def handle_sse(request):
    """SSE endpoint for browser updates"""
    session_id = request.query_params.get("session")
    if not session_id:
        session_id = request.cookies.get("mcp_map_session")
    
    if not session_id:
        session_id = str(uuid.uuid4())
        # Note: browser must handle cookie setting from response if needed, 
        # or we rely on the JS to set it initially if missing.
    
    session = get_session(session_id)
    queue = asyncio.Queue()
    session["queues"].append(queue)
    
    print(f"[MapSSE] New connection for session {session_id}")

    async def event_generator():
        # Send initial state
        yield json.dumps(session["state"])
        try:
            while True:
                data = await queue.get()
                yield json.dumps(data)
        except asyncio.CancelledError:
            print(f"[MapSSE] Closed session {session_id}")
            if queue in session["queues"]:
                session["queues"].remove(queue)

    return EventSourceResponse(event_generator())

async def serve_static(request):
    """Serve the map viewer HTML"""
    # Use importlib to find the resource within the package
    try:
        from importlib.resources import files
        html_content = files("mcp_map_server").joinpath("client.html").read_text()
        return Response(content=html_content, media_type="text/html")
    except Exception:
        # Fallback for local dev if package not installed
        html_path = Path(__file__).parent / "client.html"
        if html_path.exists():
            return Response(content=html_path.read_text(), media_type="text/html")
        return Response("client.html not found", status_code=404)

# Create Session Manager
session_manager = StreamableHTTPSessionManager(
    server, 
    stateless=False # We want to track sessions
)

@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    async with session_manager.run():
        yield

async def handle_mcp(scope, receive, send):
    """MCP endpoint using Streamable HTTP Session Manager"""
    await session_manager.handle_request(scope, receive, send)


from starlette.routing import Mount

# ...

routes = [
    Route("/events", handle_sse),
    Mount("/mcp", app=handle_mcp),
    Route("/", serve_static),
]

app = Starlette(routes=routes, lifespan=lifespan)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)

if __name__ == "__main__":
    main()
