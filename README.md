# MCP Map Server

A Model Context Protocol (MCP) server for collaborative map visualization with real-time updates.

## 🌟 Features

- **Multi-User Support**: Session-based isolation - each user has their own map state
- **Real-Time Updates**: Server-Sent Events (SSE) push changes instantly to browsers
- **Dynamic Layer Management**: Add/remove/style any MapLibre-compatible layers at runtime
- **Session Persistence**: Map state stored in Redis, survives server restarts
- **Production Ready**: Kubernetes deployment with autoscaling and health checks

## 📐 Architecture

```
User A: Claude/Copilot → MCP Server → Redis (session_a) → SSE → Browser A
User B: Claude/Copilot → MCP Server → Redis (session_b) → SSE → Browser B
```

**Key Components:**
- **MCP Server** (stdio/SSE): Exposes tools for map state management
- **Redis**: Shared state backend for session storage
- **HTTP Server**: Serves static HTML + SSE endpoint for real-time updates
- **Browser Client**: MapLibre map that consumes SSE updates

---

## 🚀 Local Development Setup

### Prerequisites

- Python 3.8+
- Docker (for Redis)
- Optional: Jupyter for notebook testing

### Step 1: Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd mcp-map-server

# Create and activate virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

**Note:** If a `.venv` directory already exists, just activate it:
```bash
source .venv/bin/activate
```

### Step 2: Start Redis

Use Docker to run Redis locally:

```bash
# Start Redis container
docker run -d --name redis-mcp \
  -p 6379:6379 \
  redis:7-alpine

# Verify Redis is running
docker ps | grep redis-mcp

# Optional: Connect to Redis CLI
docker exec -it redis-mcp redis-cli
# In Redis CLI, try: KEYS *
```

**Alternative: Install Redis locally**

- macOS: `brew install redis && brew services start redis`
- Ubuntu: `sudo apt install redis-server && sudo systemctl start redis`

### Step 3: Verify Setup (Optional)

```bash
# Run the setup test script
./test_local_setup.sh

# This will verify:
# - Virtual environment exists
# - Redis is running
# - Python dependencies are installed
```

### Step 4: Run the MCP Server

```bash
# Make sure venv is activated
source .venv/bin/activate

# Run the SSE-based server (recommended for multi-user)
python server_sse.py

# The server will:
# - Start MCP server on stdio (for LLM tools)
# - Start HTTP server on http://localhost:8081 (for browser client)
# - Connect to Redis at localhost:6379
```

You should see output like:
```
🚀 Starting MCP Map Server (SSE Mode)
✓ Connected to Redis at localhost:6379
✓ HTTP server running on http://localhost:8081
✓ MCP server ready on stdio
```

### Step 5: Open the Map Viewer

Open your browser and navigate to:

```
http://localhost:8081
```

Each browser tab/window will get a unique session ID (stored in a cookie). You can open multiple tabs to test multi-user functionality.

### Step 6: Test with Python Client

```bash
# In a new terminal, activate venv
source .venv/bin/activate

# Run the test client
python test_client.py
```

This demonstrates programmatic MCP tool usage and will:
- List available tools
- Add a raster layer (carbon data)
- Add a vector layer (WDPA protected areas)
- Apply filters and styling

---

## 🧪 Testing from Jupyter Notebook

### Create a Test Notebook

Create a file `test_mcp_notebook.ipynb`:

```python
# Cell 1: Install dependencies (if needed)
# %pip install mcp aiohttp redis

# Cell 2: Import libraries
import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# Cell 3: Connect to MCP server
async def connect_and_test():
    # Configure connection to local server
    server_params = StdioServerParameters(
        command="python",
        args=["server_sse.py"]
    )
    
    print("🔌 Connecting to MCP Map Server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"✓ Found {len(tools.tools)} tools")
            
            # Example: Add a layer with session_id
            result = await session.call_tool("add_layer", {
                "session_id": "test-notebook-session",
                "id": "wetlands",
                "type": "raster",
                "source": {
                    "type": "raster",
                    "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                    "tileSize": 256,
                    "attribution": "&copy; OpenStreetMap Contributors",
                    "minzoom": 0,
                    "maxzoom": 19
                },
                "visible": True
            })
            
            response = json.loads(result.content[0].text)
            print(f"Result: {response}")
            
            return response

# Cell 4: Run the test
# In Jupyter, you can run async code like this:
await connect_and_test()

# Or if that doesn't work, use:
# asyncio.run(connect_and_test())
```

### View Your Map

After running the notebook cells, open your browser to:

```
http://localhost:8081
```

To see your specific session, you need to set the session cookie to match your notebook session ID (`test-notebook-session` in the example above). You can do this via browser DevTools:

```javascript
// In browser console:
document.cookie = "mcp_map_session=test-notebook-session; path=/";
location.reload();
```

Or create a direct link in your notebook:

```python
# Cell 5: Generate session link
session_id = "test-notebook-session"
print(f"View your map at: http://localhost:8081?session={session_id}")
print("Note: The client_sse.html needs to be updated to read ?session parameter")
```

---

## 🔌 Connecting from VS Code / GitHub Copilot

### Configure MCP Server in VS Code

To use this MCP server with GitHub Copilot or Claude Desktop, you need to configure it in your MCP settings.

#### For GitHub Copilot (with MCP support)

Create or edit your MCP configuration file:

**Location:** `~/.config/Code/User/globalStorage/github.copilot/mcp-config.json`

```json
{
  "mcpServers": {
    "map-server": {
      "command": "python",
      "args": ["/path/to/mcp-map-server/server_sse.py"],
      "env": {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "HTTP_PORT": "8081"
      }
    }
  }
}
```

#### For Claude Desktop

Edit: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "map-server": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-map-server/server_sse.py"],
      "env": {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379"
      }
    }
  }
}
```

### Using MCP Tools in Copilot

Once configured, you can ask Copilot to interact with the map:

**Example prompts:**

> "Add a layer showing wetlands to the map"

> "Show me protected areas in California and color them by IUCN category"

> "Center the map on San Francisco and zoom to level 10"

Copilot will automatically:
1. Call the appropriate MCP tools (add_layer, filter_layer, set_map_view)
2. Include your session_id from the browser cookie
3. Update your map in real-time via SSE

### Get Your Session ID

To know which session ID to use, open the browser map viewer and check the console:

```javascript
// In browser DevTools console:
document.cookie.split('; ').find(c => c.startsWith('mcp_map_session=')).split('=')[1]
```

You can then pass this session_id explicitly when testing tools.

### Restart After Configuration

After updating your MCP configuration:
- **VS Code**: Reload window (Cmd/Ctrl + Shift + P → "Developer: Reload Window")
- **Claude Desktop**: Restart the application

---

## 📚 Available MCP Tools

The server exposes these tools for map manipulation:

### Core Tools

| Tool | Description |
|------|-------------|
| `list_layers` | List all layers for a session |
| `add_layer` | Add a new raster or vector layer |
| `remove_layer` | Remove a layer by ID |
| `set_layer_visibility` | Show/hide a layer |
| `set_map_view` | Set map center and zoom |

### Styling Tools

| Tool | Description |
|------|-------------|
| `set_layer_paint` | Update paint properties (colors, opacity, etc.) |
| `filter_layer` | Apply MapLibre filter expressions |

### Example Tool Usage

```json
// Add a PMTiles vector layer
{
  "tool": "add_layer",
  "arguments": {
    "session_id": "abc-123",
    "id": "wdpa",
    "type": "vector",
    "source": {
      "type": "vector",
      "tiles": ["https://demotiles.maplibre.org/tiles/{z}/{x}/{y}.pbf"],
      "minzoom": 0,
      "maxzoom": 5
    },
    "layers": [{
      "id": "wdpa-fill",
      "type": "fill",
      "source": "wdpa",
      "source-layer": "countries",
      "paint": {
        "fill-color": "#00ff00",
        "fill-opacity": 0.3
      }
    }]
  }
}
```

See [examples.md](examples.md) for more detailed usage scenarios.

---

## 🐛 Debugging Tips

### Check Server Logs

```bash
# Run with verbose output
python server_sse.py

# Watch for:
# - Redis connection errors
# - Tool execution logs
# - SSE connection status
```

### Verify Redis Connection

```bash
# Connect to Redis CLI
docker exec -it redis-mcp redis-cli

# List all sessions
KEYS map_state:*

# View specific session state
GET map_state:<session-id>

# See when session was last updated
GET map_state:<session-id>:updated
```

### Test SSE Connection

```bash
# Test SSE endpoint directly
curl -N http://localhost:8081/events

# Should see:
# :ping (every 15 seconds)
# And state updates when map changes
```

### Browser Console

Open browser DevTools (F12) and check:
- **Console**: Look for SSE connection messages
- **Network**: Verify `/events` connection is active (should stay open)
- **Application → Cookies**: Verify `mcp_map_session` cookie exists

### Common Issues

**"Cannot connect to Redis"**
- Ensure Docker container is running: `docker ps | grep redis`
- Check Redis port is accessible: `nc -zv localhost 6379`

**"Map not updating"**
- Verify SSE connection in browser Network tab
- Check session cookie matches the session_id used in MCP tools
- Look for errors in browser console

**"Tools not available in Copilot"**
- Verify MCP config file path is correct
- Check Python path in config is absolute
- Restart VS Code/Copilot after config changes
- Ensure `server_sse.py` is executable and dependencies installed

---

## 🏭 Production Deployment

For production deployment to Kubernetes, see [k8s/README.md](k8s/README.md).

### Quick K8s Setup

```bash
# Build and push Docker image
docker build -t your-registry/mcp-map-server:latest .
docker push your-registry/mcp-map-server:latest

# Deploy to Kubernetes
kubectl apply -f k8s/deployment.yaml

# Check deployment status
kubectl get all -n mcp-map-server

# Get external IP (if using LoadBalancer/Ingress)
kubectl get ingress -n mcp-map-server
```

### Production Considerations

When deploying to production:

1. **Authentication**: Add user authentication before session access
2. **Rate Limiting**: Prevent abuse of MCP tools (use nginx ingress annotations)
3. **Redis Security**: Enable Redis AUTH, use TLS
4. **HTTPS**: Enforce TLS for all communication
5. **CORS**: Configure appropriate origins
6. **Monitoring**: Add Prometheus metrics and Grafana dashboards
7. **Backups**: Configure Redis persistence and backups
8. **Scaling**: Use Redis cluster for high availability

Example nginx ingress with auth:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/auth-url: "https://auth.example.com/validate"
    nginx.ingress.kubernetes.io/rate-limit: "10"
```

---

## 📦 File Structure

```
mcp-map-server/
├── server_sse.py          # Multi-user SSE server (RECOMMENDED)
├── server.py              # Original polling server (prototype)
├── client_sse.html        # SSE-enabled map viewer
├── client.html            # Original polling client
├── test_client.py         # Python test client
├── test_mcp_notebook.ipynb # Jupyter notebook demo
├── test_local_setup.sh    # Local setup verification script
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container image
├── examples.md           # Detailed usage examples
├── PROGRESS.md           # Development history
├── map_state.json        # Default/fallback state file
├── .venv/                # Python virtual environment
└── k8s/                  # Kubernetes manifests
    ├── deployment.yaml   # K8s resources
    └── README.md         # Deployment guide
```

---

## 🎓 Architecture Deep Dive

### Why SSE Instead of WebSocket?

✅ **SSE Benefits:**
- Simpler protocol (just HTTP)
- Automatic reconnection built-in
- Works through proxies and firewalls
- One-way push is all we need (MCP handles client→server)
- Native browser EventSource API
- No connection management complexity

### Why Redis?

✅ **Redis Benefits:**
- Fast in-memory storage (microsecond latency)
- Simple key-value API
- Atomic operations for consistency
- Built-in persistence options
- Easy to replicate and cluster
- Widely supported in cloud/K8s environments

**Alternatives:** PostgreSQL, MongoDB, DynamoDB (AWS), Firestore (GCP)

### State Management Schema

Each session stores its map state in Redis:

```json
// Key: map_state:<session-id>
{
  "version": 1,
  "center": [lng, lat],
  "zoom": 4,
  "layers": {
    "layer-id": {
      "id": "layer-id",
      "type": "vector",
      "source": {...},
      "layers": [{...}],
      "visible": true,
      "layer_filters": {...},
      "layer_paint": {...}
    }
  }
}
```

Updates are atomic - read from Redis, modify, write back, then notify SSE connections.

---

## 🔒 Security Considerations

**Before deploying to production:**

1. **Authentication**: Session IDs should be tied to authenticated users
   ```python
   # Add JWT validation before tool execution
   @server.tool()
   async def add_layer(session_id: str, ...):
       user = validate_jwt(session_id)
       if not user:
           raise PermissionError("Unauthorized")
   ```

2. **Input Validation**: Validate layer sources and MapLibre expressions
   - Whitelist allowed tile domains
   - Validate filter expressions against schema
   - Sanitize user input

3. **Rate Limiting**: Prevent abuse
   - Limit tool calls per session/user
   - Implement backoff for failed operations

4. **Redis Security**:
   - Enable AUTH: `redis-cli CONFIG SET requirepass "strong-password"`
   - Use TLS for Redis connections
   - Restrict network access (firewall rules)

5. **HTTPS Only**: Never run production without TLS

6. **Session Management**:
   - Implement session expiration
   - Clean up old sessions from Redis
   - Limit session storage size

---

## 🚧 Future Enhancements

- [ ] Add user authentication (OAuth, JWT)
- [ ] Collaborative editing (multiple users, shared map)
- [ ] Layer templates and presets
- [ ] Undo/redo support
- [ ] State snapshots and bookmarks
- [ ] Export map as image/PDF
- [ ] Analytics and usage tracking
- [ ] Per-session rate limiting
- [ ] Layer validation against MapLibre spec
- [ ] WebSocket alternative to SSE
- [ ] Multi-region Redis replication

---

## 📄 License

See parent repository license.

## 🤝 Contributing

Contributions welcome! This is a prototype that can be extended for production use.

**Development priorities:**
1. Add comprehensive tests (unit, integration, e2e)
2. Implement authentication layer
3. Add layer validation
4. Create monitoring/observability
5. Performance optimization for large datasets
6. Documentation improvements

---

## 📞 Troubleshooting & Support

If you encounter issues:

1. Check the [debugging section](#-debugging-tips) above
2. Review [examples.md](examples.md) for usage patterns
3. Check Redis logs: `docker logs redis-mcp`
4. Verify Python dependencies: `pip list | grep -E "mcp|redis|aiohttp"`

**Common gotchas:**
- Session IDs must match between browser and MCP tool calls
- Redis must be running before starting the server
- SSE connections stay open - this is normal
- Each browser tab gets a unique session (separate cookies)
