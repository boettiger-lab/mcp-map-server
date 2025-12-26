import pytest
import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
import sys
import os

@pytest.mark.asyncio
async def test_stdio_initialization():
    """Test that the server can initialize over stdio transport."""
    # Use the current python executable to run the server module
    # We use -m to run it as a module to ensure imports work correctly
    
    # Add project root to PYTHONPATH so mcp_map_server can be found
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_root}/src:{env.get('PYTHONPATH', '')}"

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_map_server.server", "--transport", "stdio", "--port", "9999"],
        env=env
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # The initialize call is handled by the ClientSession context manager
            # but we can verify it by listing tools
            # We don't use 'await session.initialize()' because context manager does it
            # wait, ClientSession doesn't automatically initialize if not used in a specific way
            # but the context manager handles the transport.
            
            # Use initialize() explicitly to verify it works
            init_result = await session.initialize()
            assert init_result is not None
            
            # Verify we can list tools
            tools = await session.list_tools()
            assert len(tools.tools) > 0
            
            # Verify we can list prompts
            prompts = await session.list_prompts()
            assert len(prompts.prompts) > 0

            # NEW: Verify HTTP server is running in background
            import httpx
            async with httpx.AsyncClient() as client:
                # Wait a bit for background uvicorn to start
                for _ in range(10):
                    try:
                        response = await client.get("http://localhost:9999")
                        assert response.status_code == 200
                        assert "Map Viewer" in response.text
                        break
                    except Exception:
                        await asyncio.sleep(0.5)
                else:
                    pytest.fail("HTTP server not responsive in background of StdIO")
