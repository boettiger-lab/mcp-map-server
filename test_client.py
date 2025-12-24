#!/usr/bin/env python3
"""
Test client for MCP Map Server

This demonstrates how to use the MCP server programmatically.
In production, clients like Claude Desktop would connect via stdio.
"""

import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


async def test_map_server():
    """Test the MCP map server tools"""
    
    # Connect to server
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"]
    )
    
    print("🔌 Connecting to MCP Map Server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"\n✓ Found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description[:60]}...")
            
            print("\n" + "="*60)
            print("Running Tests")
            print("="*60)
            
            # Test 1: List initial layers
            print("\n1️⃣ Listing initial layers...")
            result = await session.call_tool("list_layers", {})
            response = json.loads(result.content[0].text)
            print(f"   Layers: {json.dumps(response, indent=2)}")
            
            # Test 2: Add a new raster layer
            print("\n2️⃣ Adding a raster layer (vulnerable carbon)...")
            result = await session.call_tool("add_layer", {
                "id": "carbon",
                "type": "raster",
                "source": {
                    "type": "raster",
                    "tiles": ["https://minio.carlboettiger.info/public-cog/carbon/vulnerable/{z}/{x}/{y}.png"],
                    "tileSize": 256,
                    "minzoom": 0,
                    "maxzoom": 8
                },
                "visible": True
            })
            response = json.loads(result.content[0].text)
            print(f"   Result: {response['message'] if response['success'] else response['error']}")
            
            # Test 3: Add a vector layer (PMTiles)
            print("\n3️⃣ Adding a vector layer (WDPA protected areas)...")
            result = await session.call_tool("add_layer", {
                "id": "wdpa",
                "type": "vector",
                "source": {
                    "type": "vector",
                    "url": "pmtiles://https://minio.carlboettiger.info/public-pmtiles/wdpa_global.pmtiles"
                },
                "layers": [{
                    "id": "wdpa-fill",
                    "type": "fill",
                    "source": "wdpa",
                    "source-layer": "default",
                    "paint": {
                        "fill-color": "#00ff00",
                        "fill-opacity": 0.3
                    }
                }, {
                    "id": "wdpa-outline",
                    "type": "line",
                    "source": "wdpa",
                    "source-layer": "default",
                    "paint": {
                        "line-color": "#006600",
                        "line-width": 1
                    }
                }],
                "visible": True
            })
            response = json.loads(result.content[0].text)
            print(f"   Result: {response['message'] if response['success'] else response['error']}")
            
            # Test 4: Filter the vector layer
            print("\n4️⃣ Filtering WDPA to show only IUCN category II...")
            result = await session.call_tool("filter_layer", {
                "layer_id": "wdpa-fill",
                "filter": ["==", "IUCN_CAT", "II"]
            })
            response = json.loads(result.content[0].text)
            print(f"   Result: Filtered layer '{response['layer']}'" if response['success'] else response['error'])
            
            # Test 5: Apply data-driven styling
            print("\n5️⃣ Coloring WDPA by ownership type...")
            result = await session.call_tool("set_layer_paint", {
                "layer_id": "wdpa-fill",
                "property": "fill-color",
                "value": [
                    "match",
                    ["get", "OWN_TYPE"],
                    "State", "#1f77b4",
                    "Private", "#ff7f0e",
                    "Community", "#2ca02c",
                    "Joint", "#d62728",
                    "#999999"  # default
                ]
            })
            response = json.loads(result.content[0].text)
            print(f"   Result: Set {response['property']} on {response['layer']}" if response['success'] else response['error'])
            
            # Test 6: Toggle layer visibility
            print("\n6️⃣ Hiding carbon layer...")
            result = await session.call_tool("toggle_layer", {
                "id": "carbon",
                "action": "hide"
            })
            response = json.loads(result.content[0].text)
            print(f"   Result: {response['layer']} is now {'visible' if response['visible'] else 'hidden'}" if response['success'] else response['error'])
            
            # Test 7: Get complete map state
            print("\n7️⃣ Getting complete map state...")
            result = await session.call_tool("get_map_state", {})
            response = json.loads(result.content[0].text)
            if response['success']:
                state = response['state']
                print(f"   Center: {state['center']}")
                print(f"   Zoom: {state['zoom']}")
                print(f"   Layers: {list(state['layers'].keys())}")
            
            # Test 8: Set map view
            print("\n8️⃣ Setting map view to India...")
            result = await session.call_tool("set_map_view", {
                "center": [78.9629, 20.5937],
                "zoom": 5
            })
            response = json.loads(result.content[0].text)
            print(f"   Result: Center={response['center']}, Zoom={response['zoom']}" if response['success'] else response['error'])
            
            print("\n✅ All tests completed!")
            print("\n💡 Now open http://localhost:8081 to see the map")
            print("   The client polls /api/map-state every 500ms")


if __name__ == "__main__":
    asyncio.run(test_map_server())
