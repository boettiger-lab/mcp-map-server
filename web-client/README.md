# MCP Map Server Web Client

This directory contains a simple web client that demonstrates how to use the MCP Map Server from a web browser using the **official MCP TypeScript SDK**.

## Architecture

```
Web Browser → Official MCP TypeScript SDK → StreamableHTTPClientTransport → MCP Map Server
```

The web client uses:
- **Official MCP TypeScript SDK** (`@modelcontextprotocol/sdk`) for standardized MCP communication
- **StreamableHTTPClientTransport** for HTTP-based connection to the MCP server
- **OpenAI GPT-4** for natural language understanding and tool calling
- **MapLibre GL JS** for map visualization

## Files

- `index.html` - Complete web client with MCP integration
- `README.md` - This documentation

## Setup

### 1. Using Production Deployment (Recommended)

The web client is pre-configured to connect to the production MCP Map Server deployed on Kubernetes at `https://mcp-map.nrp-nautilus.io/mcp`.

Simply open `index.html` in your web browser:

```bash
# Option 1: Open directly
open index.html

# Option 2: Serve from local HTTP server
python -m http.server 8000
# Then open http://localhost:8000
```

### 2. Using Local Development Server (Optional)

To use a local development server instead:

### Start the MCP Map Server

```bash
# From the project root
python -m mcp_map_server.server
```

This starts the MCP server with StreamableHTTP transport on `http://localhost:8081/mcp`

### 3. Configure and Connect

For production deployment:
1. Enter your OpenAI API key
2. Verify the MCP Server URL is set to `https://mcp-map.nrp-nautilus.io/mcp` (default)
3. Click "Connect"
4. Start chatting with the map assistant!

For local development:
1. Change the MCP Server URL to `http://localhost:8081/mcp`
2. Enter your OpenAI API key  
3. Click "Connect"
4. Start chatting with the map assistant!

## Usage Examples

Try these natural language requests:

- "Create a map showing protected areas in Brazil"
- "Show me US state boundaries over satellite imagery"  
- "Add a map of California's national parks"
- "Create a world map with OSM base layer"
- "Show protected areas in Costa Rica with satellite background"

## How It Works

1. **Connection**: Uses `StreamableHTTPClientTransport` to connect to the MCP server
2. **Tool Discovery**: Automatically discovers available MCP tools via `client.listTools()`
3. **Natural Language**: OpenAI GPT-4 interprets user requests and generates MCP tool calls
4. **Tool Execution**: Executes tools via `client.callTool()` using the official MCP protocol
5. **Map Updates**: Map iframe refreshes to show the updated visualization

## Production Deployment

The MCP Map Server is already deployed on Kubernetes at `https://mcp-map.nrp-nautilus.io` with:

- **TLS/SSL enabled** for secure connections
- **CORS configured** for cross-origin web client access  
- **High availability** with k8s orchestration
- **Auto-scaling** and health checks

The web client automatically connects to this production deployment.

### Custom Deployment

To deploy your own instance:

```bash
# Deploy to your k8s cluster
cd k8s
kubectl apply -f .
```

Update the MCP Server URL in the web client to point to your ingress hostname.

## Key Benefits of This Approach

✅ **Standards Compliant**: Uses official MCP TypeScript SDK
✅ **Simple**: No custom REST API wrapper needed  
✅ **Direct**: Connects directly to MCP server via StreamableHTTP
✅ **Future-Proof**: Automatically benefits from MCP protocol improvements
✅ **Discoverable**: Automatically discovers available tools from server

## Troubleshooting

### Connection Issues

- Ensure MCP server is running on the configured port with `/mcp` endpoint
- Check browser console for CORS or network errors
- Verify the MCP server supports StreamableHTTP transport

### Tool Calling Issues

- Verify OpenAI API key has sufficient credits
- Check browser console for tool execution errors
- Ensure MCP server is responding to tool calls correctly

### Map Not Loading

- Verify the base URL (without `/mcp` suffix) serves the map visualization
- Check that session IDs are being passed correctly
- Ensure map iframe can load content from the MCP server