import sys
import argparse
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession

def get_args():
    parser = argparse.ArgumentParser(description="Test MCP Map Server")
    parser.add_argument("--url", default="http://localhost:8081/mcp", help="Base URL for MCP server")
    parser.add_argument("--session", default="test-session", help="Session ID to use")
    return parser.parse_args()

async def get_client_session(url):
    """Context manager for an MCP client session"""
    return streamable_http_client(url)
