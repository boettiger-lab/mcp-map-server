import asyncio
import sys
import json
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession

async def verify_tools(session_id):
    """Verify MCP map server tools with a specific session ID"""
    # Connect to the running server via SSE/HTTP
    # Note: StreamableHTTP uses SSE for transport currently
    
    print(f"🔌 Connecting to MCP Map Server at http://localhost:8081/mcp (Session: {session_id})...")
    
    # We use the streamable_http_client helper
    async with streamable_http_client("http://localhost:8081/mcp") as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Add a raster layer
            print("1️⃣ Adding a raster layer...")
            result = await session.call_tool("add_layer", {
                "session_id": session_id,
                "id": "verify_raster",
                "type": "raster",
                "source": {
                    "type": "raster",
                    "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                    "tileSize": 256,
                    "attribution": "&copy; OpenStreetMap Contributors",
                    "minzoom": 0,
                    "maxzoom": 19
                },
                "visible": True
            })
            print(f"   Result: {result.content[0].text}")

            # Test 2: Set map view
            print("2️⃣ Setting map view...")
            result = await session.call_tool("set_map_view", {
                "session_id": session_id,
                "center": [0, 0],
                "zoom": 2
            })
            print(f"   Result: {result.content[0].text}")
            
            print("✅ Verification completed!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_tools.py <session_id>")
        sys.exit(1)
        
    asyncio.run(verify_tools(sys.argv[1]))
