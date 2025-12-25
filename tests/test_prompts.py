"""
Tests for MCP prompt functionality
"""

import os
import pytest
from mcp_map_server.server import DEFAULT_LAYER_INFO, LAYER_INFO, CORE_INSTRUCTIONS


# Import the actual handler functions from server module
# These are the decorated functions, not server methods
from mcp_map_server import server as server_module


@pytest.mark.asyncio
async def test_list_prompts():
    """Test that list_prompts returns the expected prompt"""
    # Call the decorated function directly
    prompts = await server_module.list_prompts()
    
    assert len(prompts) == 1
    assert prompts[0].name == "data_layers"
    assert prompts[0].description
    assert "data layers" in prompts[0].description.lower()
    assert prompts[0].arguments == []


@pytest.mark.asyncio
async def test_get_prompt_data_layers():
    """Test getting the data_layers prompt"""
    result = await server_module.get_prompt("data_layers", None)
    
    assert result.description
    assert len(result.messages) == 1
    assert result.messages[0].role == "user"
    assert result.messages[0].content.type == "text"
    assert result.messages[0].content.text


@pytest.mark.asyncio
async def test_get_prompt_invalid_name():
    """Test that getting an invalid prompt raises an error"""
    with pytest.raises(ValueError, match="Unknown prompt"):
        await server_module.get_prompt("invalid_prompt", None)


@pytest.mark.asyncio
async def test_default_prompt_content(monkeypatch):
    """Test that the default prompt contains expected information"""
    # Force default by unsetting env and reloading
    monkeypatch.delenv("MCP_MAP_SYSTEM_PROMPT", raising=False)
    from importlib import reload
    reload(server_module)
    
    result = await server_module.get_prompt("data_layers", None)
    prompt_text = result.messages[0].content.text
    
    # Should contain guidance about configuration
    assert "MCP_MAP_SYSTEM_PROMPT" in prompt_text
    
    # Should contain core instructions
    assert "Instructions" in prompt_text
    assert "add_layer" in prompt_text.lower()
    
    # Should contain example layer information
    assert "Protected Areas" in prompt_text or "WDPA" in prompt_text
    assert "Attributes" in prompt_text
    assert "Examples" in prompt_text
    
    # Restore state for other tests if necessary
    monkeypatch.undo()
    reload(server_module)


@pytest.mark.asyncio
async def test_custom_prompt_from_env(monkeypatch):
    """Test that custom prompt can be loaded from environment variable"""
    # Note: This test verifies the pattern works, but actual env loading
    # happens at module import time. In production, set env before starting server.
    custom_prompt = "# Custom Data Layers\n\nThis is a custom prompt for testing."
    
    # Set environment variable
    monkeypatch.setenv("MCP_MAP_SYSTEM_PROMPT", custom_prompt)
    
    # Reload the module to pick up the environment variable
    from importlib import reload
    reload(server_module)
    
    result = await server_module.get_prompt("data_layers", None)
    prompt_text = result.messages[0].content.text
    
    assert custom_prompt in prompt_text
    assert CORE_INSTRUCTIONS in prompt_text
    
    # Restore original module state
    monkeypatch.undo()
    reload(server_module)


def test_default_prompt_structure():
    """Test that the default prompt has the expected structure"""
    assert "Available Data Layers" in DEFAULT_LAYER_INFO
    assert "MCP_MAP_SYSTEM_PROMPT" in DEFAULT_LAYER_INFO
    assert "IUCN_CAT" in DEFAULT_LAYER_INFO


def test_system_prompt_loaded():
    """Test that LAYER_INFO is loaded (either from env or default)"""
    assert LAYER_INFO
    assert len(LAYER_INFO) > 0

def test_load_system_prompt_logic(tmp_path, monkeypatch):
    """Test the priority of load_system_prompt function"""
    from mcp_map_server.server import load_system_prompt, DEFAULT_LAYER_INFO
    
    # Test Default
    monkeypatch.delenv("MCP_MAP_SYSTEM_PROMPT", raising=False)
    assert load_system_prompt() == DEFAULT_LAYER_INFO
    
    # Test Env
    monkeypatch.setenv("MCP_MAP_SYSTEM_PROMPT", "env-prompt")
    assert load_system_prompt() == "env-prompt"
    
    # Test File
    p = tmp_path / "prompt.md"
    p.write_text("file-prompt")
    assert load_system_prompt(prompt_file=str(p)) == "file-prompt"
    
    # Test Text (highest priority)
    assert load_system_prompt(prompt_text="text-prompt") == "text-prompt"
    assert load_system_prompt(prompt_file=str(p), prompt_text="text-prompt") == "text-prompt"

