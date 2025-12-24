import asyncio
import sys
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def verify_tools(session_id):
    """Verify MCP map server tools with a specific session ID"""
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server_sse.py"],
        env=None
    )
    
    print(f"🔌 Connecting to MCP Map Server (Session: {session_id})...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Add a raster layer
            print("\n1️⃣ Adding a raster layer...")
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
            print("\n2️⃣ Setting map view...")
            result = await session.call_tool("set_map_view", {
                "session_id": session_id,
                "center": [0, 0],
                "zoom": 2
            })
            print(f"   Result: {result.content[0].text}")
            
            print("\n✅ Verification completed!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_tools.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    asyncio.run(verify_tools(session_id))
