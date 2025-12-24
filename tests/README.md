# MCP Map Server Tests

This directory contains verification scripts to test the MCP Map Server.

## Prerequisites

Ensure you have the dependencies installed:
```bash
pip install -r ../requirements.txt
```

## Running Tests

### 1. Minimal Connectivity Test
Checks if the MCP server is reachable and initialized.

**Local:**
```bash
python test_connectivity.py
```

**Kubernetes (with port-forwarding):**
```bash
# First, forward the port
kubectl port-forward svc/mcp-map-server 8081:8081 &

python test_connectivity.py --url http://localhost:8081/mcp
```

**Kubernetes (Public Ingress):**
```bash
python test_connectivity.py --url https://mcp-map.nrp-nautilus.io/mcp
```

### 2. Full Tool Verification
Tests actual map operations (`add_layer`, `set_map_view`, etc.).

**Local:**
```bash
python test_tools.py
```

**Kubernetes:**
```bash
python test_tools.py --url https://mcp-map.nrp-nautilus.io/mcp
```

## Files
-   `common.py`: Shared utilities (CLI args, client session helper).
-   `test_connectivity.py`: Simple connection check.
-   `test_tools.py`: Comprehensive functional test.
