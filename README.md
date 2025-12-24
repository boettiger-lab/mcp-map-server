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

1.  **Install dependencies:**
    ```bash
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    ```

2.  **Start the server:**
    ```bash
    python server.py
    ```

3.  **Open the Map:**
    Navigate to `http://localhost:8081` in your browser.

4.  **Connect an MCP Client:**
    Configure your MCP client (e.g., Claude Desktop, Cursor, or a custom script) to connect to `http://localhost:8081/mcp/`.

### Verification

Run the included verification script to test the tools:

```bash
python verify_tools.py test-session
```

This will:
1.  Connect to the server via MCP.
2.  Add a sample raster layer (OpenStreetMap).
3.  Center the map.
4.  You should see the map update in your browser (ensure you set the session cookie if testing isolated sessions).

### Deployment (Kubernetes)

1.  **Deploy:**
    ```bash
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    kubectl apply -f k8s/ingress.yaml
    ```

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

**Running on Kubernetes:**
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
