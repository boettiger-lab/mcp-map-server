import pytest
import json

pytestmark = pytest.mark.asyncio

async def test_connectivity(mcp_client):
    """Test that we can connect to the server and list tools."""
    tools = await mcp_client.list_tools()
    assert len(tools.tools) > 0
    
    # Verify expected tools exist
    tool_names = [tool.name for tool in tools.tools]
    assert "add_layer" in tool_names
    assert "remove_layer" in tool_names
    assert "set_map_view" in tool_names
    assert "list_layers" in tool_names

async def test_add_raster_layer(mcp_client):
    """Test adding a raster layer."""
    result = await mcp_client.call_tool("add_layer", {
        "session_id": "test-session",
        "id": "osm-test",
        "type": "raster",
        "source": {
            "type": "raster",
            "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            "tileSize": 256
        }
    })
    
    response = json.loads(result.content[0].text)
    assert response["success"] is True
    assert "Added layer" in response["message"]

async def test_add_vector_layer(mcp_client):
    """Test adding a vector layer."""
    result = await mcp_client.call_tool("add_layer", {
        "session_id": "test-session-2",
        "id": "vector-test",
        "type": "vector",
        "source": {
            "type": "vector",
            "url": "https://demotiles.maplibre.org/tiles/tiles.json"
        }
    })
    
    response = json.loads(result.content[0].text)
    assert response["success"] is True
    assert "Added layer" in response["message"]

async def test_set_map_view(mcp_client):
    """Test setting map view."""
    result = await mcp_client.call_tool("set_map_view", {
        "session_id": "test-session-3",
        "center": [-122.4194, 37.7749],
        "zoom": 10
    })
    
    response = json.loads(result.content[0].text)
    assert response["success"] is True
    assert response["center"] == [-122.4194, 37.7749]

async def test_list_layers(mcp_client):
    """Test listing layers."""
    # First add a layer
    await mcp_client.call_tool("add_layer", {
        "session_id": "test-session-4",
        "id": "test-layer",
        "type": "raster",
        "source": {
            "type": "raster",
            "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            "tileSize": 256
        }
    })
    
    # Now list layers
    result = await mcp_client.call_tool("list_layers", {
        "session_id": "test-session-4"
    })
    
    response = json.loads(result.content[0].text)
    assert response["success"] is True
    assert "test-layer" in response["layers"]

async def test_remove_layer(mcp_client):
    """Test removing a layer."""
    # First add a layer
    await mcp_client.call_tool("add_layer", {
        "session_id": "test-session-5",
        "id": "layer-to-remove",
        "type": "raster",
        "source": {
            "type": "raster",
            "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            "tileSize": 256
        }
    })
    
    # Now remove it
    result = await mcp_client.call_tool("remove_layer", {
        "session_id": "test-session-5",
        "id": "layer-to-remove"
    })
    
    response = json.loads(result.content[0].text)
    assert response["success"] is True
    assert "Removed layer" in response["message"]
