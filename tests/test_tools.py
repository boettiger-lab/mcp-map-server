import asyncio
import json
import sys
from common import get_args, get_client_session
from mcp.client.session import ClientSession

async def test_tools():
    args = get_args()
    print(f"🛠️  Testing Tools on {args.url} (Session: {args.session})...")
    
    try:
        async with await get_client_session(args.url) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 1. Add Raster Layer
                print("\n1️⃣  Testing add_layer (Raster)...")
                result = await session.call_tool("add_layer", {
                    "session_id": args.session,
                    "id": "osm-test",
                    "type": "raster",
                    "source": {
                        "type": "raster",
                        "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                        "tileSize": 256
                    }
                })
                print(f"   Result: {result.content[0].text}")

                # 2. Add Vector Layer
                print("\n2️⃣  Testing add_layer (Vector)...")
                result = await session.call_tool("add_layer", {
                    "session_id": args.session,
                    "id": "vector-test",
                    "type": "vector",
                    "source": {
                        "type": "vector",
                        "url": "https://demotiles.maplibre.org/tiles/tiles.json"
                    }
                })
                print(f"   Result: {result.content[0].text}")

                # 3. Set Map View
                print("\n3️⃣  Testing set_map_view...")
                result = await session.call_tool("set_map_view", {
                    "session_id": args.session,
                    "center": [-122.4194, 37.7749],
                    "zoom": 10
                })
                print(f"   Result: {result.content[0].text}")

                # 4. List Layers
                print("\n4️⃣  Testing list_layers...")
                result = await session.call_tool("list_layers", {
                    "session_id": args.session
                })
                print(f"   Result: {result.content[0].text}")

                print("\n✅ All Tool Tests Completed!")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_tools())
