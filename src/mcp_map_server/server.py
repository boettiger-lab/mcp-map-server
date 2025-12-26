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
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from mcp.server import Server, NotificationOptions
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent, Prompt, PromptMessage, GetPromptResult
from mcp.server.models import InitializationOptions
import mcp.types as types

# --- Global In-Memory State ---
sessions = {}
VIEWER_BASE_URL = "http://localhost:8081"

def get_session(session_id: str, default_state: dict | None = None):
    if session_id not in sessions:
        sessions[session_id] = {
            "state": default_state or {
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

# --- Configuration ---
CORE_INSTRUCTIONS = """# MCP Map Server - Instructions

This server provides tools to control a MapLibre GL JS map viewer. Each tool maps directly to MapLibre GL JS concepts.

- **add_layer**: Use this to add a MapLibre source and its associated layers in one call.
- **Source IDs**: The `id` you provide is used as the MapLibre `source-id`. 
- **Sub-layers**: For vector sources, you MUST provide an array of MapLibre layer objects in the `layers` property. For each sub-layer, the `source` property will automatically be set to your layer `id` if you omit it.
- **Coordinates**: All coordinates are [Longitude, Latitude] (WGS84).
"""

DEFAULT_LAYER_INFO = """# Available Data Layers

You have access to map visualization tools that can display geospatial data layers.

*Note: These layer definitions can be customized by setting the `MCP_MAP_SYSTEM_PROMPT` environment variable with your own layer information.*

## Base Layers (Raster)

### OpenStreetMap Standard
- **ID**: `osm`
- **Type**: Raster
- **URL**: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
- **Attribution**: `© OpenStreetMap contributors`
- **Description**: Standard OpenStreetMap tiles with streets, labels, and geographic features

### OpenStreetMap Humanitarian
- **ID**: `osm-humanitarian`
- **Type**: Raster  
- **URL**: `https://tile-{s}.openstreetmap.fr/hot/{z}/{x}/{y}.png`
- **Subdomains**: `a,b,c`
- **Attribution**: `© OpenStreetMap contributors, Tiles courtesy of Humanitarian OpenStreetMap Team`
- **Description**: High-contrast humanitarian style, good for overlaying data

### CartoDB Positron (Light)
- **ID**: `carto-light`
- **Type**: Raster
- **URL**: `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`
- **Subdomains**: `a,b,c,d`
- **Attribution**: `© OpenStreetMap contributors © CARTO`
- **Description**: Light grayscale base map, excellent for data visualization

### Esri World Imagery
- **ID**: `esri-satellite`
- **Type**: Raster
- **URL**: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
- **Attribution**: `Tiles © Esri`
- **Description**: High-resolution satellite imagery

## Vector Data Layers

### World Database on Protected Areas (WDPA)
- **ID**: `wdpa`
- **Type**: Vector
- **URL**: `pmtiles://https://s3-west.nrp-nautilus.io/public-wdpa/WDPA_Dec2025.pmtiles`
- **Source Layer**: `wdpa`
- **Description**: Global protected areas dataset with IUCN categorization and management information

**Attributes:**
- `IUCN_CAT`: IUCN management category (Ia=Strict Nature Reserve, Ib=Wilderness Area, II=National Park, III=Natural Monument, IV=Habitat Management, V=Protected Landscape, VI=Sustainable Use)
- `OWN_TYPE`: Ownership type (State, Private, Community, etc.)
- `ISO3`: ISO 3166-1 alpha-3 country code
- `STATUS_YR`: Year of establishment or designation
- `NAME`: Protected area name
- `DESIG_ENG`: Designation in English (e.g., National Park, Wildlife Sanctuary)

### Overture Maps - Administrative Boundaries
- **ID**: `overture-admins`
- **Type**: Vector
- **URL**: `pmtiles://https://overturemaps.azureedge.net/release/2024-11-13.0/theme=admins.pmtiles`
- **Source Layer**: `admins`
- **Description**: Administrative boundary polygons including countries, states/regions, and counties

**Attributes:**
- `admin_level`: Administrative level (2=country, 4=state/region, 6=county)
- `names`: Name information in multiple languages
- `iso_country_code_alpha_2`: ISO country code
- `iso_sub_country_code`: Sub-country codes

### Overture Maps - Places
- **ID**: `overture-places`  
- **Type**: Vector
- **URL**: `pmtiles://https://overturemaps.azureedge.net/release/2024-11-13.0/theme=places.pmtiles`
- **Source Layer**: `places`
- **Description**: Points of interest including businesses, landmarks, and facilities

**Attributes:**
- `categories`: Category classification
- `names`: Place names in multiple languages
- `confidence`: Data confidence score

### Natural Earth Countries (50m)
- **ID**: `ne-countries`
- **Type**: Vector
- **URL**: `pmtiles://https://cdn.protomaps.com/data/ne-50m-countries.pmtiles`
- **Source Layer**: `countries`
- **Description**: Country boundaries at 1:50m scale from Natural Earth

**Attributes:**
- `NAME`: Country name
- `ISO_A2`: ISO Alpha-2 country code
- `POP_EST`: Population estimate
- `GDP_MD`: GDP in millions USD
- `CONTINENT`: Continent name

## Example Usage Patterns

**Create a base map:**
```json
{
  "tool": "add_layer",
  "arguments": {
    "id": "osm-base",
    "type": "raster",
    "source": {
      "type": "raster",
      "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      "attribution": "© OpenStreetMap contributors"
    }
  }
}
```

**Add protected areas in a specific country:**
```json
{
  "tool": "add_layer", 
  "arguments": {
    "id": "wdpa",
    "type": "vector",
    "source": {
      "type": "vector",
      "url": "pmtiles://https://s3-west.nrp-nautilus.io/public-wdpa/WDPA_Dec2025.pmtiles"
    },
    "layers": [{
      "id": "wdpa-fill",
      "type": "fill",
      "source": "wdpa",
      "source-layer": "wdpa",
      "paint": {"fill-color": "green", "fill-opacity": 0.5}
    }]
  }
}
```

**Filter to specific country (e.g., USA):**
```json
{
  "tool": "filter_layer",
  "arguments": {
    "layer_id": "wdpa",
    "filter": ["==", ["get", "ISO3"], "USA"]
  }
}
```

**Style by attribute (e.g., IUCN category):**
```json
{
  "tool": "set_layer_paint",
  "arguments": {
    "layer_id": "wdpa",
    "property": "fill-color",
    "value": [
      "match",
      ["get", "IUCN_CAT"],
      "II", "#2ca02c",
      "IV", "#1f77b4", 
      "V", "#ff7f0e",
      "#999999"
    ]
  }
}
```

## Tips for Layer Selection

- **Always start with a base layer** (OSM, CartoDB, or Esri)
- **Use light base maps** (carto-light) when overlaying lots of data
- **Use satellite imagery** (esri-satellite) for environmental or geographic context
- **PMTiles sources** are efficient for large vector datasets
- **Filter by geography** first (ISO3, admin_level) to improve performance
- **Use meaningful colors** and opacity for multiple overlapping layers
"""

def load_system_prompt(prompt_file: str | None = None, prompt_text: str | None = None) -> str:
    """
    Load dynamic layer information from various sources.
    Priority: prompt_text > prompt_file > MCP_MAP_SYSTEM_PROMPT > DEFAULT_LAYER_INFO
    """
    if prompt_text:
        return prompt_text
    
    if prompt_file:
        file_path = Path(prompt_file)
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        return file_path.read_text()
    
    env_prompt = os.getenv("MCP_MAP_SYSTEM_PROMPT")
    if env_prompt:
        return env_prompt
    
    return DEFAULT_LAYER_INFO

# Initialize dynamic layer info (can be overridden in main())
LAYER_INFO = load_system_prompt()


# --- MCP Server ---
server = Server("mcp-map-server-stream")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available map control tools"""
    return [
        Tool(
            name="add_layer",
            description="Add a MapLibre source and one or more layers. Maps to `map.addSource()` and `map.addLayer()`.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID (default: 'default')"},
                    "state": {"type": "string", "description": "Optional initial map state JSON string."},
                    "id": {"type": "string", "description": "Unique identifier for the source and logical layer."},
                    "type": {"type": "string", "enum": ["raster", "vector"], "description": "The type of data source."},
                    "source": {"type": "object", "description": "MapLibre source configuration (e.g. {type: 'vector', url: '...'})"},
                    "layers": {"type": "array", "items": {"type": "object"}, "description": "Array of MapLibre layer objects. If omitted for 'raster', a default layer is created."},
                    "visible": {"type": "boolean", "default": True, "description": "Initial visibility."}
                },
                "required": ["id", "type", "source"]
            }
        ),
        Tool(
            name="remove_layer",
            description="Remove a layer and its associated source from the map.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The session ID."},
                    "state": {"type": "string", "description": "Optional map state JSON string."},
                    "id": {"type": "string", "description": "The ID of the layer/source to remove."}
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="set_map_view",
            description="Move the map camera to a specific center and zoom level.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The session ID."},
                    "state": {"type": "string", "description": "Optional map state JSON string."},
                    "center": {"type": "array", "items": {"type": "number"}, "description": "[longitude, latitude] array."},
                    "zoom": {"type": "number", "description": "Zoom level (e.g. 0-22)."}
                },
                "required": []
            }
        ),
        Tool(
            name="list_layers",
            description="List all currently active layers in the session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The session ID."},
                    "state": {"type": "string", "description": "Optional map state JSON string."}
                }
            }
        ),
        Tool(
            name="filter_layer",
            description="Apply a MapLibre filter expression to a layer and all its sub-layers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The session ID."},
                    "state": {"type": "string", "description": "Optional map state JSON string."},
                    "layer_id": {"type": "string", "description": "The ID of the layer to filter."},
                    "filter": {"description": "MapLibre filter expression (e.g. ['==', 'property', 'value'])"}
                },
                "required": ["layer_id", "filter"]
            }
        ),
         Tool(
            name="set_layer_paint",
            description="Set MapLibre paint properties (e.g. colors, opacity) for a layer and all its sub-layers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The session ID."},
                    "state": {"type": "string", "description": "Optional map state JSON string."},
                    "layer_id": {"type": "string", "description": "The ID of the layer to style."},
                    "property": {"type": "string", "description": "The paint property name (e.g. 'fill-color', 'raster-opacity')."},
                    "value": {"description": "The new value for the paint property."}
                },
                "required": ["layer_id", "property", "value"]
            }
        ),
        Tool(
            name="get_map_config",
            description="Return the current map configuration as a JSON string for inspection or as 'state' for other tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "The session ID."},
                    "state": {"type": "string", "description": "Optional map state JSON string."}
                }
            }
        )
    ]

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts for the map server"""
    return [
        Prompt(
            name="data_layers",
            description="Information about available map data layers, their attributes, and how to use them",
            arguments=[]
        )
    ]

@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    """Get a prompt by name"""
    if name != "data_layers":
        raise ValueError(f"Unknown prompt: {name}")
    
    # Combine fixed core instructions with dynamic layer information
    full_prompt = f"{CORE_INSTRUCTIONS}\n\n{LAYER_INFO}"
    
    return GetPromptResult(
        description="Core instructions and information about available map data layers",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=full_prompt
                )
            )
        ]
    )


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    # Extract inputs
    session_id = arguments.get("session_id", "default")
    input_state_str = arguments.get("state")
    
    # Logic for stateless vs stateful
    is_stateless = input_state_str is not None
    
    if is_stateless:
        try:
            state = json.loads(input_state_str)
            session_id = None # Do not notify any active sessions if stateless
        except json.JSONDecodeError:
            return [TextContent(type="text", text=f"Error: Invalid 'state' JSON provided")]
    else:
        session = get_session(session_id)
        state = session["state"]

    try:
        if name == "add_layer":
            layer_id = arguments["id"]
            layer_type = arguments["type"]
            source = arguments["source"]
            layers = arguments.get("layers", [])
            visible = arguments.get("visible", True)
            
            if layer_type == "raster" and not layers:
                layers = [{"id": layer_id, "type": "raster", "source": layer_id}]
            
            # Ensure all sub-layers have the correct source ID
            injected_layers = []
            for lyr in layers:
                if not isinstance(lyr, dict):
                    injected_layers.append(lyr)
                    continue
                new_lyr = dict(lyr)
                if not new_lyr.get("source"):
                    new_lyr["source"] = layer_id
                injected_layers.append(new_lyr)
            layers = injected_layers
            
            state["layers"][layer_id] = {
                "id": layer_id,
                "type": layer_type,
                "visible": visible,
                "source": source,
                "layers": layers,
                "layer_paint": {},
                "layer_filters": {}
            }
            state["version"] += 1

        elif name == "remove_layer":
            layer_id = arguments["id"]
            if layer_id in state["layers"]:
                del state["layers"][layer_id]
                state["version"] += 1

        elif name == "set_map_view":
            center = arguments.get("center")
            zoom = arguments.get("zoom")
            if center:
                state["center"] = center
            if zoom is not None:
                state["zoom"] = zoom
            if center or zoom is not None:
                state["version"] += 1

        elif name == "filter_layer":
            layer_id = arguments["layer_id"]
            filter_expr = arguments["filter"]
            if layer_id in state["layers"]:
                layer_config = state["layers"][layer_id]
                # Reset filters and apply to all sub-layers
                layer_config["layer_filters"] = {}
                for sl in layer_config.get("layers", []):
                    layer_config["layer_filters"][sl["id"]] = filter_expr
                if not layer_config.get("layers"):
                    layer_config["layer_filters"][layer_id] = filter_expr
                state["version"] += 1

        elif name == "set_layer_paint":
            layer_id = arguments["layer_id"]
            prop = arguments["property"]
            val = arguments["value"]
            if layer_id in state["layers"]:
                layer_config = state["layers"][layer_id]
                if "layer_paint" not in layer_config:
                    layer_config["layer_paint"] = {}
                
                for sl in layer_config.get("layers", []):
                    if sl["id"] not in layer_config["layer_paint"]:
                        layer_config["layer_paint"][sl["id"]] = {}
                    layer_config["layer_paint"][sl["id"]][prop] = val
                
                if not layer_config.get("layers"):
                    if layer_id not in layer_config["layer_paint"]:
                        layer_config["layer_paint"][layer_id] = {}
                    layer_config["layer_paint"][layer_id][prop] = val
                state["version"] += 1

        elif name == "list_layers":
            lyr_list = list(state["layers"].keys())
            return [TextContent(type="text", text=f"Layers: {lyr_list}")]
            
        elif name == "get_map_config":
            pass # We return the state anyway

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        # Notify if stateful
        if not is_stateless and session_id:
            await notify_session(session_id, state)
            
        # Always return the full updated state as JSON
        state_json = json.dumps(state, indent=2)
        
        # Build viewer URL
        viewer_url = VIEWER_BASE_URL
        if not is_stateless and session_id:
            viewer_url = f"{viewer_url}/?session={session_id}"
        
        return [
            TextContent(
                type="text", 
                text=f"Success. View map at: {viewer_url}\n\nUpdated map configuration:\n\n```json\n{state_json}\n```\n\nYou can use this JSON in a MapViewer or as the 'state' argument for follow-up tool calls."
            )
        ]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


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

# Add CORS middleware for browser access
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id", "mcp-protocol-version"],  # Expose MCP headers to browser
        allow_credentials=True,
    )
]

app = Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


async def run_stdio(host: str = "0.0.0.0", port: int = 8081):
    from mcp.server.stdio import stdio_server
    import uvicorn
    
    # Start HTTP server in background so viewer remains accessible
    config = uvicorn.Config(app, host=host, port=port, log_level="error")
    http_server = uvicorn.Server(config)
    background_task = asyncio.create_task(http_server.serve())
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-map-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
    
    # Clean up background server
    http_server.should_exit = True
    await background_task

def main():
    import uvicorn
    import argparse
    global LAYER_INFO, VIEWER_BASE_URL
    
    parser = argparse.ArgumentParser(description="MCP Map Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio", help="Transport to use (stdio or http)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8081, help="Port to bind to")
    parser.add_argument("--base-url", help="Public base URL for the viewer links (e.g. https://map.example.com)")
    parser.add_argument("--prompt", help="System prompt text")
    parser.add_argument("--prompt-file", help="Path to system prompt markdown file")
    
    args = parser.parse_args()
    
    # Set global base URL for tool links
    if args.base_url:
        VIEWER_BASE_URL = args.base_url.rstrip("/")
    else:
        # Default to localhost if not provided
        host_part = "localhost" if args.host == "0.0.0.0" else args.host
        VIEWER_BASE_URL = f"http://{host_part}:{args.port}"

    # Update global LAYER_INFO based on CLI args
    try:
        LAYER_INFO = load_system_prompt(prompt_file=args.prompt_file, prompt_text=args.prompt)
    except Exception as e:
        print(f"Error loading prompt: {e}")
        import sys
        sys.exit(1)
        
    if args.transport == "stdio":
        asyncio.run(run_stdio(host=args.host, port=args.port))
    else:
        print(f"Starting HTTP server on {args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
