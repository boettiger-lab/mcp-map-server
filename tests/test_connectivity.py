import asyncio
import sys
from common import get_args, get_client_session
from mcp.client.session import ClientSession

async def test_connectivity():
    args = get_args()
    print(f"🔌 Testing connectivity to {args.url}...")
    
    try:
        async with await get_client_session(args.url) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connection Successful!")
                
                # Basic check: List tools
                tools = await session.list_tools()
                print(f"✅ Found {len(tools.tools)} tools.")
                
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_connectivity())
