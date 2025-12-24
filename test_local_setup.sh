#!/bin/bash
# Test script for local MCP server setup

echo "=========================================="
echo "MCP Map Server - Local Setup Test"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found at .venv"
    echo "   Create it with: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "✓ Virtual environment found"

# Activate venv
source .venv/bin/activate

# Check Python version
PYTHON_VERSION=$(python --version)
echo "✓ Python version: $PYTHON_VERSION"

# Check if Redis is running
echo ""
echo "Checking Redis..."
if docker ps | grep -q redis; then
    echo "✓ Redis container is running"
    REDIS_CONTAINER=$(docker ps | grep redis | awk '{print $1}')
    echo "  Container ID: $REDIS_CONTAINER"
else
    echo "❌ Redis container not running"
    echo "   Start it with: docker run -d --name redis-mcp -p 6379:6379 redis:7-alpine"
    exit 1
fi

# Test Redis connectivity
echo ""
echo "Testing Redis connectivity..."
if docker exec $REDIS_CONTAINER redis-cli ping | grep -q PONG; then
    echo "✓ Redis is responding"
else
    echo "❌ Redis is not responding"
    exit 1
fi

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
python -c "import mcp, aiohttp, redis, aiohttp_sse" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ All required Python packages installed"
else
    echo "❌ Missing Python packages"
    echo "   Install with: pip install -r requirements.txt"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All prerequisites are met!"
echo "=========================================="
echo ""
echo "To start the server:"
echo "  python server_sse.py"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:8081"
echo ""
echo "To test with the Python client:"
echo "  python test_client.py"
echo ""
echo "To test with Jupyter notebook:"
echo "  jupyter notebook test_mcp_notebook.ipynb"
echo ""
