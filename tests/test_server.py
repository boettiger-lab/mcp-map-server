import pytest
import json
import re

pytestmark = pytest.mark.asyncio

def extract_json_state(text: str) -> dict:
    """Helper to extract JSON from the markdown block in tool output"""
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find JSON block in tool output: {text}")
    return json.loads(match.group(1))

async def test_connectivity(mcp_client):
    """Test that we can connect to the server and list tools."""
    tools = await mcp_client.list_tools()
    assert len(tools.tools) > 0
    
    # Verify expected tools exist
    tool_names = [tool.name for tool in tools.tools]
    assert "add_layer" in tool_names
    assert "remove_layer" in tool_names
    assert "set_map_view" in tool_names
    assert "get_map_config" in tool_names

async def test_add_raster_layer(mcp_client):
    """Test adding a raster layer and receiving full state."""
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
    
    output = result.content[0].text
    assert "Success" in output
    assert "View map at: http://localhost:8081/?session=test-session" in output
    state = extract_json_state(output)
    assert "osm-test" in state["layers"]
    assert state["layers"]["osm-test"]["type"] == "raster"

async def test_set_map_view(mcp_client):
    """Test setting map view."""
    result = await mcp_client.call_tool("set_map_view", {
        "session_id": "view-session",
        "center": [-122.4194, 37.7749],
        "zoom": 10
    })
    
    state = extract_json_state(result.content[0].text)
    assert state["center"] == [-122.4194, 37.7749]
    assert state["zoom"] == 10

async def test_session_isolation(mcp_client):
    """Test that two sessions don't bleed into each other."""
    # Add layer to session A
    await mcp_client.call_tool("add_layer", {
        "session_id": "session-A",
        "id": "layer-A",
        "type": "raster",
        "source": {"type": "raster", "tiles": ["..."]}
    })
    
    # Add different layer to session B
    await mcp_client.call_tool("add_layer", {
        "session_id": "session-B",
        "id": "layer-B",
        "type": "raster",
        "source": {"type": "raster", "tiles": ["..."]}
    })
    
    # Verify A only has A
    res_a = await mcp_client.call_tool("get_map_config", {"session_id": "session-A"})
    state_a = extract_json_state(res_a.content[0].text)
    assert "layer-A" in state_a["layers"]
    assert "layer-B" not in state_a["layers"]
    
    # Verify B only has B
    res_b = await mcp_client.call_tool("get_map_config", {"session_id": "session-B"})
    state_b = extract_json_state(res_b.content[0].text)
    assert "layer-B" in state_b["layers"]
    assert "layer-A" not in state_b["layers"]

async def test_stateless_transformation(mcp_client):
    """Test passing a 'state' JSON string for stateless operation."""
    initial_state = json.dumps({
        "version": 1,
        "center": [0, 0],
        "zoom": 1,
        "layers": {}
    })
    
    result = await mcp_client.call_tool("add_layer", {
        "state": initial_state,
        "id": "stateless-layer",
        "type": "raster",
        "source": {"type": "raster", "tiles": ["..."]}
    })
    
    output_state = extract_json_state(result.content[0].text)
    assert "stateless-layer" in output_state["layers"]
    assert output_state["center"] == [0, 0]
    
    # Verify it didn't touch the 'default' session
    default_res = await mcp_client.call_tool("get_map_config", {"session_id": "default"})
    default_state = extract_json_state(default_res.content[0].text)
    assert "stateless-layer" not in default_state["layers"]

async def test_remove_layer(mcp_client):
    """Test removing a layer."""
    session_id = "remove-session"
    await mcp_client.call_tool("add_layer", {
        "session_id": session_id,
        "id": "target",
        "type": "raster",
        "source": {"type": "raster", "tiles": ["..."]}
    })
    
    result = await mcp_client.call_tool("remove_layer", {
        "session_id": session_id,
        "id": "target"
    })
    
    state = extract_json_state(result.content[0].text)
    assert "target" not in state["layers"]
