import os
import threading
import time
import pytest
import pytest_asyncio
import uvicorn
from starlette.testclient import TestClient
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp_map_server.server import app

# We use a real TCP port for the threaded server because the mcp client
# expects a URL to connect to.
TEST_HOST = "127.0.0.1"
TEST_PORT = 8082
TEST_URL = f"http://{TEST_HOST}:{TEST_PORT}/mcp"

@pytest.fixture(scope="session")
def map_server():
    """Starts the MCP Map Server in a background thread."""
    config = uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="error")
    server = uvicorn.Server(config)
    
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    
    # Wait for server to start
    # Ideally we'd ping it, but a short sleep is robust enough for simple tests
    time.sleep(1)
    
    yield
    
    server.should_exit = True
    thread.join(timeout=2)

@pytest_asyncio.fixture
async def mcp_client(map_server):
    """Provides a connected MCP ClientSession."""
    # Manually manage context managers to avoid task scope issues
    streams_context = streamable_http_client(TEST_URL)
    streams = await streams_context.__aenter__()
    
    try:
        read, write = streams[0], streams[1]
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        
        yield session
        
    finally:
        # Clean up in reverse order
        try:
            await session.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            await streams_context.__aexit__(None, None, None)
        except Exception:
            pass
