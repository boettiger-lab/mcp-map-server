# Developer Guide & Contributing

This document provides a technical overview of the `mcp-map-server` codebase for developers and contributors.

## Architecture Overview

The **MCP Map Server** is designed to provide map visualization capabilities via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). 

It implements a "Streamable HTTP" architecture:
1.  **MCP Server**: Exposes tools (like `add_layer`, `set_map_view`) that an AI assistant can call.
2.  **SSE Endpoint**: Serves Server-Sent Events at `/events` to push state changes to a web client.
3.  **Map Client**: A simple HTML/JS frontend (`client.html`) that connects to the SSE endpoint to render the map state using MapLibre/Leaflet.

### Current Limitation: The "Query" Tool
The project includes a `system-prompt.md` that instructs the AI to use a **`query`** tool for DuckDB SQL analysis of h3-indexed parquet data. 
> [!IMPORTANT]
> The `query` tool is **NOT** currently implemented in `server.py`. The system assumes the presence of a separate DuckDB MCP server or that this functionality will be added in the future.

## File Structure

### Core Package (`src/mcp_map_server/`)
*   **`server.py`**: The main entry point. Initializes the Starlette app, defines the MCP tools (`add_layer`, etc.), manages session state in-memory, and handles the SSE transport.
*   **`client.html`**: The static frontend viewer served at the root `/`. It connects to `/events` to receive map updates.
*   **`__init__.py`**: Package initialization file.

### Configuration
*   **`pyproject.toml`**: Modern Python package configuration with dependencies and build settings.
*   **`system-prompt.md`**: A **manual** reference file containing the system instructions for the AI. It is **not loaded** by the server code; it exists to be copied into the AI client's configuration manually.

### Kubernetes Deployment (`k8s/`)
Deployment manifests for running the server on a cluster:
*   **`k8s/deployment.yaml`**: Defines the Pod spec, replicas, and container image.
*   **`k8s/service.yaml`**: ClusterIP service to expose the pods internally.
*   **`k8s/ingress.yaml`**: Ingress rules for external access.

### Testing (`tests/`)
*   **`tests/conftest.py`**: Pytest fixtures, including a background server fixture for integration tests.
*   **`tests/test_server.py`**: Comprehensive test suite covering connectivity and all MCP tools.

### CI/CD
*   **`.github/workflows/ci.yml`**: GitHub Actions workflow for automated testing on Python 3.10, 3.11, and 3.12.

### Miscellaneous
*   **`examples.md`**: Documentation and hypothetical usage examples.
*   **`show_california.py`**: A standalone Python client script demonstrating how to interact with the map server programmatically.
*   **`test_mcp_notebook.ipynb`**: A Jupyter notebook for interactive testing or demos.

## Development Workflow

### Setting Up

1. **Clone the repository:**
   ```bash
   git clone https://github.com/boettiger-lab/mcp-map-server.git
   cd mcp-map-server
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install in editable mode with dev dependencies:**
   ```bash
   pip install -e .[dev]
   ```

### Running Tests

Run the full test suite:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_server.py
```

The tests automatically spin up a server on port 8082, so you don't need to start the server manually.

### Code Changes

When making changes to the server:

1. Make your changes in `src/mcp_map_server/`
2. Run tests to ensure nothing broke: `pytest`
3. If adding new functionality, add corresponding tests in `tests/test_server.py`
4. The package is installed in editable mode, so changes are immediately reflected

### Continuous Integration

All pull requests and pushes to `main` or `develop` branches automatically trigger the CI workflow, which:
- Tests on Python 3.10, 3.11, and 3.12
- Ensures all tests pass before merging

