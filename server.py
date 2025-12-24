#!/usr/bin/env python3
"""
MCP Map Server - Manages MapLibre map state via MCP tools

This server exposes MCP tools that modify a shared map state object.
A separate HTTP server provides:
1. Static HTML serving (map viewer)
2. REST API for map state retrieval (/api/map-state)

Clients poll the API and update their maps based on server state.
"""

import asyncio
import json
import os
from typing import Any
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from aiohttp import web

# Global map state
STATE_FILE = Path(__file__).parent / "map_state.json"
map_state = {
    "version": 1,
    "center": [-98.5795, 39.8283],  # Center of US
    "zoom": 4,
    "layers": {
        # Example layer pre-configured
        "example-wetlands": {
            "id": "example-wetlands",
            "type": "raster",
            "visible": True,
            "source": {
                "type": "raster",
                "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                "tileSize": 256,
                "attribution": "&copy; OpenStreetMap Contributors",
                "minzoom": 0,
                "maxzoom": 19
            },
            "paint": {}
        }
    }
}


def load_state():
    """Load map state from disk"""
    global map_state
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                map_state = json.load(f)
            print(f"✓ Loaded state from {STATE_FILE}")
        except Exception as e:
            print(f"⚠ Could not load state: {e}, using defaults")


def save_state():
    """Persist map state to disk"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(map_state, f, indent=2)
        print(f"✓ Saved state to {STATE_FILE}")
    except Exception as e:
        print(f"❌ Could not save state: {e}")


# Initialize state on startup
load_state()

# Create MCP server
server = Server("mcp-map-server")


# ============================================================================
# MCP Tools
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available map control tools"""
    return [
        Tool(
            name="add_layer",
            description="Add a new map layer (raster or vector). Supports MapLibre source types: raster, vector, geojson, pmtiles. You can add multiple MapLibre layers (fill, line, circle) for a single source by providing a layers array.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique identifier for this layer group"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["raster", "vector"],
                        "description": "Layer type: raster (tiles) or vector (geojson/pmtiles)"
                    },
                    "source": {
                        "type": "object",
                        "description": "MapLibre source specification. For raster: {type: 'raster', tiles: ['url'], tileSize: 256}. For vector: {type: 'geojson', data: 'url'} or {type: 'vector', url: 'pmtiles://url'}"
                    },
                    "layers": {
                        "type": "array",
                        "description": "Array of MapLibre layer specs (for vector sources). Each has: id, type (fill/line/circle), source-layer (for vector tiles), paint, layout. For raster, leave empty or omit.",
                        "items": {"type": "object"}
                    },
                    "visible": {
                        "type": "boolean",
                        "description": "Whether layer should be visible initially (default: true)"
                    }
                },
                "required": ["id", "type", "source"]
            }
        ),
        Tool(
            name="remove_layer",
            description="Remove a layer from the map by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The layer ID to remove"
                    }
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="toggle_layer",
            description="Toggle visibility of an existing layer",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The layer ID to toggle"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["show", "hide", "toggle"],
                        "description": "Action: show, hide, or toggle current state"
                    }
                },
                "required": ["id", "action"]
            }
        ),
        Tool(
            name="list_layers",
            description="List all layers and their current visibility status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="filter_layer",
            description="Apply a MapLibre filter expression to a vector layer. Filters use array syntax: ['==', 'property', 'value'], ['in', 'prop', 'val1', 'val2'], ['>=', 'prop', 100], ['all', [...], [...]]",
            inputSchema={
                "type": "object",
                "properties": {
                    "layer_id": {
                        "type": "string",
                        "description": "The MapLibre layer ID to filter (for vector layers with multiple sublayers, specify the specific layer ID like 'wdpa-fill')"
                    },
                    "filter": {
                        "description": "MapLibre filter expression as JSON array, e.g., ['==', 'IUCN_CAT', 'II'] or null to clear"
                    }
                },
                "required": ["layer_id"]
            }
        ),
        Tool(
            name="set_layer_paint",
            description="Set paint properties for a layer. Use MapLibre expressions for data-driven styling: ['match', ['get', 'prop'], 'val1', 'color1', 'val2', 'color2', 'default']",
            inputSchema={
                "type": "object",
                "properties": {
                    "layer_id": {
                        "type": "string",
                        "description": "The MapLibre layer ID to style"
                    },
                    "property": {
                        "type": "string",
                        "description": "Paint property name (e.g., 'fill-color', 'line-width', 'circle-radius')"
                    },
                    "value": {
                        "description": "Paint value - can be static (e.g., '#ff0000') or MapLibre expression"
                    }
                },
                "required": ["layer_id", "property", "value"]
            }
        ),
        Tool(
            name="reset_layer_style",
            description="Reset a layer's filter and paint properties to defaults",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The layer group ID to reset"
                    }
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="get_map_state",
            description="Get the complete current map state including all layers and their configurations",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_layer_info",
            description="Get detailed information about a specific layer",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The layer ID to query"
                    }
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="set_map_view",
            description="Set the map center and zoom level",
            inputSchema={
                "type": "object",
                "properties": {
                    "center": {
                        "type": "array",
                        "description": "Map center as [longitude, latitude]",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "zoom": {
                        "type": "number",
                        "description": "Zoom level (0-22)"
                    }
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute map control tools"""
    
    try:
        if name == "add_layer":
            layer_id = arguments["id"]
            layer_type = arguments["type"]
            source = arguments["source"]
            layers = arguments.get("layers", [])
            visible = arguments.get("visible", True)
            
            # For raster layers, create a simple layer entry
            if layer_type == "raster" and not layers:
                layers = [{
                    "id": layer_id,
                    "type": "raster",
                    "source": layer_id
                }]
            
            map_state["layers"][layer_id] = {
                "id": layer_id,
                "type": layer_type,
                "visible": visible,
                "source": source,
                "layers": layers,
                "paint": {},
                "filter": None
            }
            save_state()
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": f"Added layer '{layer_id}'",
                    "layer": map_state["layers"][layer_id]
                })
            )]
        
        elif name == "remove_layer":
            layer_id = arguments["id"]
            if layer_id in map_state["layers"]:
                del map_state["layers"][layer_id]
                save_state()
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "message": f"Removed layer '{layer_id}'"
                    })
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Layer '{layer_id}' not found"
                    })
                )]
        
        elif name == "toggle_layer":
            layer_id = arguments["id"]
            action = arguments["action"]
            
            if layer_id not in map_state["layers"]:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Layer '{layer_id}' not found"
                    })
                )]
            
            layer = map_state["layers"][layer_id]
            if action == "toggle":
                layer["visible"] = not layer["visible"]
            else:
                layer["visible"] = (action == "show")
            
            save_state()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "layer": layer_id,
                    "visible": layer["visible"]
                })
            )]
        
        elif name == "list_layers":
            layers_info = {
                layer_id: {
                    "type": layer["type"],
                    "visible": layer["visible"],
                    "has_filter": layer.get("filter") is not None,
                    "has_custom_paint": bool(layer.get("paint", {}))
                }
                for layer_id, layer in map_state["layers"].items()
            }
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "layers": layers_info
                })
            )]
        
        elif name == "filter_layer":
            layer_id = arguments["layer_id"]
            filter_expr = arguments.get("filter")
            
            # Find the layer group that contains this layer ID
            layer_group = None
            for group_id, group in map_state["layers"].items():
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
                    text=json.dumps({
                        "success": False,
                        "error": f"Layer '{layer_id}' not found"
                    })
                )]
            
            # Store filter at the layer level (applies to specific sublayer)
            if "layer_filters" not in layer_group:
                layer_group["layer_filters"] = {}
            layer_group["layer_filters"][layer_id] = filter_expr
            
            save_state()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "layer": layer_id,
                    "filter": filter_expr
                })
            )]
        
        elif name == "set_layer_paint":
            layer_id = arguments["layer_id"]
            property_name = arguments["property"]
            value = arguments["value"]
            
            # Find the layer group
            layer_group = None
            for group_id, group in map_state["layers"].items():
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
                    text=json.dumps({
                        "success": False,
                        "error": f"Layer '{layer_id}' not found"
                    })
                )]
            
            # Store paint properties per-layer
            if "layer_paint" not in layer_group:
                layer_group["layer_paint"] = {}
            if layer_id not in layer_group["layer_paint"]:
                layer_group["layer_paint"][layer_id] = {}
            
            layer_group["layer_paint"][layer_id][property_name] = value
            
            save_state()
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
            if layer_id not in map_state["layers"]:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Layer '{layer_id}' not found"
                    })
                )]
            
            layer = map_state["layers"][layer_id]
            layer["filter"] = None
            layer["paint"] = {}
            layer["layer_filters"] = {}
            layer["layer_paint"] = {}
            
            save_state()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": f"Reset style for layer '{layer_id}'"
                })
            )]
        
        elif name == "get_map_state":
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "state": map_state
                })
            )]
        
        elif name == "get_layer_info":
            layer_id = arguments["id"]
            if layer_id in map_state["layers"]:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "layer": map_state["layers"][layer_id]
                    })
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Layer '{layer_id}' not found"
                    })
                )]
        
        elif name == "set_map_view":
            if "center" in arguments:
                map_state["center"] = arguments["center"]
            if "zoom" in arguments:
                map_state["zoom"] = arguments["zoom"]
            
            save_state()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "center": map_state["center"],
                    "zoom": map_state["zoom"]
                })
            )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"Unknown tool: {name}"
                })
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


# ============================================================================
# HTTP Server for Static Files + API
# ============================================================================

async def serve_map_state(request):
    """API endpoint: GET /api/map-state"""
    return web.json_response(map_state)


async def serve_static(request):
    """Serve the static HTML viewer"""
    html_path = Path(__file__).parent / "client.html"
    if html_path.exists():
        return web.FileResponse(html_path)
    else:
        return web.Response(text="client.html not found", status=404)


async def start_http_server():
    """Start the HTTP server for API and static serving"""
    app = web.Application()
    app.router.add_get('/api/map-state', serve_map_state)
    app.router.add_get('/', serve_static)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8081)
    await site.start()
    print("✓ HTTP server running on http://localhost:8081")
    print("  - Map viewer: http://localhost:8081/")
    print("  - API: http://localhost:8081/api/map-state")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run both MCP server (stdio) and HTTP server"""
    # Start HTTP server in background
    asyncio.create_task(start_http_server())
    
    # Run MCP server (stdio)
    print("✓ MCP server starting on stdio")
    print("  Use with: mcp serve or Claude Desktop")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
