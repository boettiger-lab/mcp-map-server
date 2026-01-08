# MCP Map Server

A Model Context Protocol (MCP) server that provides a dynamic map interface. This robust Python server enables AI agents to control a MapLibre GL JS - based map viewer, allowing for real-time visualization of geospatial data.


## Features

-   **Interactive Map**: Powered by MapLibre GL JS for high-performance vector and raster mapping.
-   **Tooling**: Provides MCP tools to:
    -   Add/Remove layers (Raster & Vector)
    -   Set map view (Center & Zoom)
    -   Filter data
    -   Style layers
-   **In-Memory State**: Simple, stateless deployment model (ideal for K8s).


## Quick Start

### Local Development

1.  **Start the server:**
    ```bash
    uv run mcp-map-server
    ```

3.  **Open the Map:**
    Navigate to `http://localhost:8081` in your browser.

4.  **Connect an MCP Client:**
    Configure your MCP client (e.g., Claude Desktop, Cursor, or a custom script) to connect to `http://localhost:8081/mcp/`.



## Architecture

1.  **MCP Server (`server.py`)**: A `Starlette` application that:
    -   Exposes an MCP endpoint at `/mcp` (Streamable HTTP).
    -   Exposes an SSE endpoint at `/events` for the browser.
    -   Serves the static map viewer at `/`.
    -   Maintains map state in-memory.

2.  **MCP Client (AI Agent)**: Connects to `/mcp` to call tools and modify the map state.

3.  **Map Viewer (Browser)**: Connects to `/events` to receive state updates and render them using MapLibre GL JS.

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

## Architecture: Independent Maps

The MCP Map Server follows a **Tool-Centric** model. Instead of one shared map, it provides tools that help clients manage their own independent map configurations.

### Core Usage Scenarios

1.  **Local Private Map (VSCode/Local Agent)**
    - Run the server locally: `mcp-map-server`
    - View your map at: `http://localhost:8081/`
    - Everything stays on your machine. Your local AI agent updates your local browser via SSE.

2.  **Private Session on Public Server**
    - Visit the shared server with a unique session ID: 
      `https://mcp-map.nrp-nautilus.io/?session=my-private-uuid`
    - Tell your AI agent to use this `session_id`.
    - Only you (and whoever has the ID) will see the updates.

3.  **Stateless/Unhosted (Web Developers)**
    - For clients like **LangChain-js** or custom web apps.
    - Pass an existing map JSON string as the `state` argument to any tool.
    - The tool returns the **full updated JSON** without saving anything to the server's memory.
    - Your app can then render this JSON using its own viewer component.

---

## Tooling & API

Every map-modifying tool returns the **full, updated map configuration** in JSON format. 

### Available Tools

- `add_layer`: Adds a raster (XYZ/Tiles) or vector (MVT/PMTiles) layer.
- `set_map_view`: Moves the camera to a specific `center` and `zoom`.
- `filter_layer`: Applies MapLibre filter expressions to an existing layer.
- `set_layer_paint`: Dynamically modifies paint properties (colors, opacity, etc.).
- `remove_layer`: Deletes a layer by ID.
- `get_map_config`: Returns the current session/provided state as JSON.

### MCP Client Configuration

To use this with MCP-compatible clients like Claude Desktop or VSCode extensions, point them to the server.

**Local Development (Recommended):**

Local clients like Claude Desktop and VSCode expect **StdIO** transport when launching a command. The server now defaults to `stdio`.


```json
{
  "mcpServers": {
    "map-server": {
      "command": "uv run mcp-map-server"
    }
  }
}
```

**Passing CLI Arguments (Transport, Prompts, etc.):**

If you need to specify the transport explicitly or provide a custom system prompt file, use the `args` array. 

> [!IMPORTANT]
> Arguments must be passed as individual elements in the `args` array, NOT as part of the `command` string.

```json
{
  "mcpServers": {
    "map-server": {
      "command": "uv run mcp-map-server",
      "args": [
        "--transport", "stdio",
        "--prompt-file", "/path/to/my-layers.md"
      ]
    }
  }
}
```

*Note: The server defaults to `stdio` when run as a command.*

**Using the Shared Production Server:**

Web-based or remote clients connect via **HTTP**.

```json
{
  "mcpServers": {
    "map-server": {
      "url": "https://mcp-map.nrp-nautilus.io/mcp/"
    }
  }
}
```

## License

MIT
