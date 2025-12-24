#!/usr/bin/env python3
"""
Show a map of California using the MCP Map Server
"""

import asyncio
import json
import uuid
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


async def show_california_map():
    """Display a map centered on California"""
    
    # Generate a unique session ID
    session_id = f"california-{uuid.uuid4().hex[:8]}"
    
    # Connect to server
    server_params = StdioServerParameters(
        command="python",
        args=["server_sse.py"]
    )
    
    print("🔌 Connecting to MCP Map Server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print(f"📍 Session ID: {session_id}")
            
            # Set map view to California
            # California center coordinates: approximately -119.4179, 36.7783
            print("\n🗺️  Setting map view to California...")
            result = await session.call_tool("set_map_view", {
                "session_id": session_id,
                "center": [-119.4179, 36.7783],
                "zoom": 6
            })
            response = json.loads(result.content[0].text)
            if response['success']:
                print(f"   ✓ Map centered at {response['center']} with zoom {response['zoom']}")
            else:
                print(f"   ✗ Error: {response.get('error', 'Unknown error')}")
            
            # Add California National Parks GeoJSON layer
            print("\n🏞️  Adding California National Parks...")
            result = await session.call_tool("add_layer", {
                "session_id": session_id,
                "id": "ca-parks",
                "type": "vector",
                "source": {
                    "type": "geojson",
                    "data": "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/california-county-boundaries.geojson"
                },
                "layers": [{
                    "id": "ca-counties-fill",
                    "type": "fill",
                    "source": "ca-parks",
                    "paint": {
                        "fill-color": "#3b82f6",
                        "fill-opacity": 0.2
                    }
                }, {
                    "id": "ca-counties-outline",
                    "type": "line",
                    "source": "ca-parks",
                    "paint": {
                        "line-color": "#1e40af",
                        "line-width": 2
                    }
                }],
                "visible": True
            })
            response = json.loads(result.content[0].text)
            print(f"   ✓ {response['message']}" if response['success'] else f"   ✗ Error: {response.get('error', 'Unknown error')}")
            
            # Add terrain/hillshade layer using USGS data
            print("\n⛰️  Adding terrain layer...")
            result = await session.call_tool("add_layer", {
                "session_id": session_id,
                "id": "terrain",
                "type": "raster",
                "source": {
                    "type": "raster",
                    "tiles": ["https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"],
                    "tileSize": 256,
                    "minzoom": 0,
                    "maxzoom": 16
                },
                "visible": True
            })
            response = json.loads(result.content[0].text)
            print(f"   ✓ {response['message']}" if response['success'] else f"   ✗ Error: {response.get('error', 'Unknown error')}")
            
            # List all layers
            print("\n📋 Current map layers:")
            result = await session.call_tool("list_layers", {
                "session_id": session_id
            })
            response = json.loads(result.content[0].text)
            if response['success']:
                for layer_id, layer_info in response['layers'].items():
                    visibility = "👁️" if layer_info.get('visible', True) else "🚫"
                    print(f"   {visibility} {layer_id} ({layer_info.get('type', 'unknown')})")
            
            # Generate browser link
            print(f"\n🌐 View your map in browser:")
            print(f"   1. Open: http://localhost:8081")
            print(f"   2. Open browser console (F12)")
            print(f"   3. Run: document.cookie = \"mcp_map_session={session_id}; path=/\"; location.reload();")
            print(f"\n   Or visit: http://localhost:8081 and paste this in console:")
            print(f"   document.cookie = \"mcp_map_session={session_id}\"; location.reload();")
            
            print("\n✅ California map is ready!")
            print("   The map shows:")
            print("   - Base map of California")
            print("   - County boundaries in blue")
            print("   - USGS satellite imagery")


if __name__ == "__main__":
    asyncio.run(show_california_map())
