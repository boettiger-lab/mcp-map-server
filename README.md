# MCP Map Server

A Model Context Protocol (MCP) server that provides a dynamic map interface. This robust Python server enables AI agents to control a MapLibre GL JS - based map viewer, allowing for real-time visualization of geospatial data.

![Map View](https://github.com/boettiger-lab/mcp-map-server/raw/main/docs/map-view.png)

## Features

-   **MCP & HTTP Support**: Implements the Model Context Protocol using `StreamableHTTPServerTransport`.
-   **Real-time Updates**: Uses Server-Sent Events (SSE) to push map state changes to the browser instantly.
-   **Interactive Map**: Powered by MapLibre GL JS for high-performance vector and raster mapping.
-   **Tooling**: Provides MCP tools to:
    -   Add/Remove layers (Raster & Vector)
    -   Set map view (Center & Zoom)
    -   Filter data
    -   Style layers
-   **In-Memory State**: Simple, stateless deployment model (ideal for K8s).

## Architecture

1.  **MCP Server (`server.py`)**: A `Starlette` application that:
    -   Exposes an MCP endpoint at `/mcp` (Streamable HTTP).
    -   Exposes an SSE endpoint at `/events` for the browser.
    -   Serves the static map viewer at `/`.
    -   Maintains map state in-memory.

2.  **MCP Client (AI Agent)**: Connects to `/mcp` to call tools and modify the map state.

3.  **Map Viewer (Browser)**: Connects to `/events` to receive state updates and render them using MapLibre GL JS.

## Quick Start

### Local Development

1.  **Clone and install:**
    ```bash
    git clone https://github.com/boettiger-lab/mcp-map-server.git
    cd mcp-map-server
    python -m venv .venv
    source .venv/bin/activate
    pip install -e .[dev]
    ```

2.  **Start the server:**
    ```bash
    mcp-map-server
    ```

3.  **Open the Map:**
    Navigate to `http://localhost:8081` in your browser.

4.  **Connect an MCP Client:**
    Configure your MCP client (e.g., Claude Desktop, Cursor, or a custom script) to connect to `http://localhost:8081/mcp/`.

### Running Tests

Run the test suite with:

```bash
pytest
```

The tests will automatically start a test server on port 8082.

### Configuring Data Layer Information

The server supports MCP prompts to provide AI agents with information about available data layers. This helps agents understand which layers are available, their attributes, and how to use them effectively.

**Recommended: Use a Markdown file**

You can provide a system prompt as a plain markdown file:

```bash
mcp-map-server --prompt-file my-layers.md
```

**Set via environment variable:**

This is useful for containerized deployments:

```bash
export MCP_MAP_SYSTEM_PROMPT="$(cat my-layers.md)"
mcp-map-server
```

**Direct string argument:**

```bash
mcp-map-server --prompt "# Available Layers\n\n- wdpa: Protected Areas..."
```

See `system-prompt.example.md` for a complete example of layer configuration.

### Deployment (Kubernetes)

1.  **Deploy:**
    ```bash
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    kubectl apply -f k8s/ingress.yaml
    ```

    The ConfigMap `mcp-map-config` should contain your system prompt markdown in the `system-prompt` key.

## Tool Usage / Configuration

### VSCode (Claude/Cline) & Claude Desktop

To use this tool with MCP-compatible clients (like Claude Desktop or the Claude extension for VSCode), add the following to your MCP configuration file (e.g., `claude_desktop_config.json`):

**Running Locally:**
```json
{
  "mcpServers": {
    "map-server": {
      "url": "http://localhost:8081/mcp/"
    }
  }
}
```

**Using the deployed server from NRP:**
```json
{
  "mcpServers": {
    "map-server": {
      "url": "https://mcp-map.nrp-nautilus.io/mcp/"
    }
  }
}
```

### API & Tools

See [examples.md](examples.md) for detailed JSON payloads for all available tools.

-   `add_layer`: Add raster (XYZ) or vector (MVT/PMTiles) layers.
-   `remove_layer`: Remove a layer by ID.
-   `set_map_view`: Fly to a location.
-   `list_layers`: Get current layer state.
-   `filter_layer`: Apply MapLibre filters.
-   `set_layer_paint`: Change layer styling.

## License

MIT
