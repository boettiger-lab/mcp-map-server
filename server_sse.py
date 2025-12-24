#!/usr/bin/env python3
"""
MCP Map Server - Multi-User SSE Version

Features:
- Session-based state (isolated per user)
- Redis for state persistence
- SSE for real-time updates to browsers
- Production-ready for K8s deployment
"""

import asyncio
import json
import os
import uuid
from typing import Any, Optional
from pathlib import Path
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from aiohttp import web
from aiohttp_sse import sse_response
import redis.asyncio as aioredis

# Configuration from environment
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
HTTP_PORT = int(os.getenv('HTTP_PORT', '8081'))
SESSION_COOKIE = 'mcp_map_session'

# Redis client (initialized in startup)
redis_client: Optional[aioredis.Redis] = None

# Active SSE connections by session
sse_connections = {}

# Create MCP server
server = Server("mcp-map-server-sse")


def get_default_state():
    """Default map state for new sessions"""
    return {
        "version": 1,
        "center": [-98.5795, 39.8283],
        "zoom": 4,
        "layers": {}
    }


async def get_redis():
    """Get Redis client, create if needed"""
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


async def get_session_state(session_id: str) -> dict:
    """Load state for a session from Redis"""
    r = await get_redis()
    state_json = await r.get(f"map_state:{session_id}")
    
    if state_json:
        return json.loads(state_json)
    else:
        # New session - create default state
        default_state = get_default_state()
        await save_session_state(session_id, default_state)
        return default_state


async def save_session_state(session_id: str, state: dict):
    """Save state for a session to Redis"""
    r = await get_redis()
    state_json = json.dumps(state)
    await r.set(f"map_state:{session_id}", state_json)
    
    # Also update timestamp
    await r.set(f"map_state:{session_id}:updated", datetime.utcnow().isoformat())
    
    # Notify SSE connections for this session
    await notify_session(session_id, state)


async def notify_session(session_id: str, state: dict):
    """Send state update to all SSE connections for this session"""
    if session_id in sse_connections:
        for queue in sse_connections[session_id]:
            try:
                await queue.put(state)
            except Exception as e:
                print(f"Error notifying SSE connection: {e}")


# ============================================================================
# MCP Tools (now session-aware)
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available map control tools"""
    return [
        Tool(
            name="add_layer",
            description="Add a new map layer for a specific session. Include session_id parameter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "User's session ID"
                    },
                    "id": {
                        "type": "string",
                        "description": "Unique identifier for this layer"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["raster", "vector"],
                        "description": "Layer type"
                    },
                    "source": {
                        "type": "object",
                        "description": "MapLibre source specification"
                    },
                    "layers": {
                        "type": "array",
                        "description": "Array of MapLibre layer specs",
                        "items": {"type": "object"}
                    },
                    "visible": {
                        "type": "boolean",
                        "description": "Initial visibility"
                    }
                },
                "required": ["session_id", "id", "type", "source"]
            }
        ),
        Tool(
            name="remove_layer",
            description="Remove a layer from a session's map",
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
            name="toggle_layer",
            description="Toggle layer visibility in a session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "id": {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": ["show", "hide", "toggle"]
                    }
                },
                "required": ["session_id", "id", "action"]
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
            description="Apply MapLibre filter to a layer in a session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "layer_id": {"type": "string"},
                    "filter": {"description": "MapLibre filter expression"}
                },
                "required": ["session_id", "layer_id"]
            }
        ),
        Tool(
            name="set_layer_paint",
            description="Set paint properties for a layer in a session",
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
        ),
        Tool(
            name="reset_layer_style",
            description="Reset layer styling in a session",
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
            name="get_map_state",
            description="Get complete map state for a session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="set_map_view",
            description="Set map center/zoom for a session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "center": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "zoom": {"type": "number"}
                },
                "required": ["session_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute map control tools with session isolation"""
    
    try:
        session_id = arguments.get("session_id")
        if not session_id:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "session_id is required"
                })
            )]
        
        # Load session state
        state = await get_session_state(session_id)
        
        # Execute tool (similar logic to original server.py)
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
            
            await save_session_state(session_id, state)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": f"Added layer '{layer_id}' to session {session_id}",
                    "layer": state["layers"][layer_id]
                })
            )]
        
        elif name == "remove_layer":
            layer_id = arguments["id"]
            if layer_id in state["layers"]:
                del state["layers"][layer_id]
                await save_session_state(session_id, state)
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": True, "message": f"Removed layer '{layer_id}'"})
                )]
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Layer '{layer_id}' not found"})
            )]
        
        elif name == "toggle_layer":
            layer_id = arguments["id"]
            action = arguments["action"]
            
            if layer_id not in state["layers"]:
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": f"Layer '{layer_id}' not found"})
                )]
            
            layer = state["layers"][layer_id]
            if action == "toggle":
                layer["visible"] = not layer["visible"]
            else:
                layer["visible"] = (action == "show")
            
            await save_session_state(session_id, state)
            return [TextContent(
                type="text",
                text=json.dumps({"success": True, "layer": layer_id, "visible": layer["visible"]})
            )]
        
        elif name == "list_layers":
            layers_info = {
                lid: {
                    "type": l["type"],
                    "visible": l["visible"],
                    "has_filter": l.get("filter") is not None,
                    "has_custom_paint": bool(l.get("paint", {}))
                }
                for lid, l in state["layers"].items()
            }
            return [TextContent(
                type="text",
                text=json.dumps({"success": True, "layers": layers_info})
            )]
        
        elif name == "filter_layer":
            layer_id = arguments["layer_id"]
            filter_expr = arguments.get("filter")
            
            # Find layer group
            layer_group = None
            for group_id, group in state["layers"].items():
                if group.get("layers"):
                    if any(l.get("id") == layer_id for l in group["layers"]):
                        layer_group = group
                        break
                elif group.get("id") == layer_id:
                    layer_group = group
                    break
            
            if not layer_group:
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": f"Layer '{layer_id}' not found"})
                )]
            
            if "layer_filters" not in layer_group:
                layer_group["layer_filters"] = {}
            layer_group["layer_filters"][layer_id] = filter_expr
            
            await save_session_state(session_id, state)
            return [TextContent(
                type="text",
                text=json.dumps({"success": True, "layer": layer_id, "filter": filter_expr})
            )]
        
        elif name == "set_layer_paint":
            layer_id = arguments["layer_id"]
            property_name = arguments["property"]
            value = arguments["value"]
            
            # Find layer group
            layer_group = None
            for group_id, group in state["layers"].items():
                if group.get("layers"):
                    if any(l.get("id") == layer_id for l in group["layers"]):
                        layer_group = group
                        break
                elif group.get("id") == layer_id:
                    layer_group = group
                    break
            
            if not layer_group:
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": f"Layer '{layer_id}' not found"})
                )]
            
            if "layer_paint" not in layer_group:
                layer_group["layer_paint"] = {}
            if layer_id not in layer_group["layer_paint"]:
                layer_group["layer_paint"][layer_id] = {}
            
            layer_group["layer_paint"][layer_id][property_name] = value
            
            await save_session_state(session_id, state)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "layer": layer_id,
                    "property": property_name,
                    "value": value
                })
            )]
        
        elif name == "reset_layer_style":
            layer_id = arguments["id"]
            if layer_id not in state["layers"]:
                return [TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": f"Layer '{layer_id}' not found"})
                )]
            
            layer = state["layers"][layer_id]
            layer["filter"] = None
            layer["paint"] = {}
            layer["layer_filters"] = {}
            layer["layer_paint"] = {}
            
            await save_session_state(session_id, state)
            return [TextContent(
                type="text",
                text=json.dumps({"success": True, "message": f"Reset style for layer '{layer_id}'"})
            )]
        
        elif name == "get_map_state":
            return [TextContent(
                type="text",
                text=json.dumps({"success": True, "state": state})
            )]
        
        elif name == "set_map_view":
            if "center" in arguments:
                state["center"] = arguments["center"]
            if "zoom" in arguments:
                state["zoom"] = arguments["zoom"]
            
            await save_session_state(session_id, state)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "center": state["center"],
                    "zoom": state["zoom"]
                })
            )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Unknown tool: {name}"})
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


# ============================================================================
# HTTP Server with SSE
# ============================================================================

async def handle_sse(request):
    """SSE endpoint - streams map state updates to browser"""
    # Get or create session
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        session_id = str(uuid.uuid4())
    
    print(f"[SSE] New connection for session {session_id}")
    
    # Create queue for this connection
    queue = asyncio.Queue()
    
    # Register connection
    if session_id not in sse_connections:
        sse_connections[session_id] = []
    sse_connections[session_id].append(queue)
    
    async with sse_response(request) as resp:
        # Set session cookie
        resp.set_cookie(SESSION_COOKIE, session_id, max_age=86400*7)  # 7 days
        
        # Send initial state
        state = await get_session_state(session_id)
        await resp.send(json.dumps(state))
        
        # Stream updates
        try:
            while True:
                state = await queue.get()
                await resp.send(json.dumps(state))
        except asyncio.CancelledError:
            print(f"[SSE] Connection closed for session {session_id}")
        finally:
            # Clean up
            if session_id in sse_connections:
                sse_connections[session_id].remove(queue)
                if not sse_connections[session_id]:
                    del sse_connections[session_id]
    
    return resp


async def serve_static(request):
    """Serve the map viewer HTML"""
    html_path = Path(__file__).parent / "client_sse.html"
    if html_path.exists():
        return web.FileResponse(html_path)
    return web.Response(text="client_sse.html not found", status=404)


async def health_check(request):
    """Health check endpoint for K8s"""
    try:
        r = await get_redis()
        await r.ping()
        return web.json_response({"status": "healthy", "redis": "connected"})
    except Exception as e:
        return web.json_response(
            {"status": "unhealthy", "error": str(e)},
            status=503
        )


async def start_http_server():
    """Start HTTP server with SSE support"""
    app = web.Application()
    app.router.add_get('/events', handle_sse)
    app.router.add_get('/health', health_check)
    app.router.add_get('/', serve_static)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', HTTP_PORT)
    await site.start()
    print(f"✓ HTTP server running on http://0.0.0.0:{HTTP_PORT}")
    print(f"  - Map viewer: http://localhost:{HTTP_PORT}/")
    print(f"  - SSE stream: http://localhost:{HTTP_PORT}/events")
    print(f"  - Health: http://localhost:{HTTP_PORT}/health")


async def main():
    """Run MCP server and HTTP server"""
    # Initialize Redis
    await get_redis()
    print(f"✓ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    
    # Start HTTP server
    asyncio.create_task(start_http_server())
    
    # Run MCP server
    print("✓ MCP server starting on stdio")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
