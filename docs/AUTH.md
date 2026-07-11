# Authentication — operator and agent runbooks

See also [AUTH_DESIGN.md](AUTH_DESIGN.md) and [AUTH_TEST_MATRIX.md](AUTH_TEST_MATRIX.md).

## Operator configuration

| Variable | Required when | Description |
|----------|---------------|-------------|
| `MCP_AUTH_MODE` | always | `lime` (production), `legacy` (deprecated), or `none` (dev only) |
| `MCP_RESOURCE_SERVER_URL` | `lime` | Public URL of this MCP RS (e.g. `https://mcp.byteask.ai`) |
| `LIME_BASE_URL` | `lime` | LIME OAuth issuer (default `https://lime.pics`) |
| `LIME_OAUTH_AUDIENCE` | `lime` | JWT audience (default `mcp`) |
| `MCP_HTTP_AUTH_TOKEN` | `legacy` | Deprecated shared secret |
| `MCP_ALLOWED_HOSTS` | HTTP prod | Comma-separated allowed `Host` values |

### Production deploy checklist

```bash
MCP_AUTH_MODE=lime
MCP_RESOURCE_SERVER_URL=https://mcp.byteask.ai
MCP_ALLOWED_HOSTS=mcp.byteask.ai
LIME_BASE_URL=https://lime.pics
LIME_OAUTH_AUDIENCE=mcp
```

## LIME is M2M-only

**LIME is a non-standard OAuth 2.1 provider for M2M agents.** No browser redirects.
Agents obtain an MCP JWT via `POST /modules/oauth/token` with `X-Agent-Token` and an
empty body, or via the SDK.

Flow:

1. Agent presents `X-Agent-Token` to LIME → receives short-lived MCP JWT (`sub=agent_id`, `aud=mcp`).
2. Agent calls `POST /mcp` with `Authorization: Bearer <jwt>`.
3. ByteAsk RS verifies JWT via JWKS (`lime-mcp-server-sdk`).

PRM is served at `/.well-known/oauth-protected-resource`.

## Agent integration

### Option A — SDK as MCP client (recommended)

```python
from lime_agents import LimeAgent

agent = LimeAgent(agent_token=os.environ["LIME_AGENT_TOKEN"])
tools = await agent.list_tools("https://mcp.byteask.ai/mcp")
result = await agent.call_tool(
    "https://mcp.byteask.ai/mcp",
    "search_docs",
    {"query": "STM32", "limit": 5},
)
await agent.aclose()
```

### Option B — Manual token (low-level HTTP)

```python
jwt = (await agent.get_mcp_access_token()).access_token
# Authorization: Bearer {jwt} on POST /mcp
```

## Local smoke

```bash
./scripts/smoke_lime_http.sh
```

Or manually:

```bash
MCP_AUTH_MODE=lime MCP_RESOURCE_SERVER_URL=http://127.0.0.1:8000 \
  MCP_ALLOWED_HOSTS=127.0.0.1,localhost \
  uv run byteask-embedded-mcp --transport http
```

## Legacy mode (deprecated)

`MCP_AUTH_MODE=legacy` with `MCP_HTTP_AUTH_TOKEN` wraps the Streamable HTTP app
with a shared-secret middleware. Migrate to `lime` before the next major release.
