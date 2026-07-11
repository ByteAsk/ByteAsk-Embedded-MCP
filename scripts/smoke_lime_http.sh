#!/usr/bin/env bash
# Local smoke for MCP_AUTH_MODE=lime (PRM + 401 without token).
set -euo pipefail

export MCP_AUTH_MODE=lime
export MCP_RESOURCE_SERVER_URL=http://127.0.0.1:8000
export MCP_ALLOWED_HOSTS=127.0.0.1,localhost
export LIME_BASE_URL=https://lime.pics

echo "Starting ByteAsk MCP (lime mode) on :8000..."
python -m byteask_embedded_mcp.server --transport http &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT

sleep 2

echo "=== PRM ==="
curl -s "http://127.0.0.1:8000/.well-known/oauth-protected-resource" | jq .

echo "=== POST /mcp without token (expect 401) ==="
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}' \
  "http://127.0.0.1:8000/mcp"

echo "Smoke complete."
