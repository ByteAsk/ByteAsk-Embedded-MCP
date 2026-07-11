# Upstream PR: LIME OAuth 2.1 Resource Server

**Title:** `feat(auth): replace stub bearer with LIME OAuth 2.1 + agent identity`

## Problem

- HTTP transport used a shared static bearer token (`MCP_HTTP_AUTH_TOKEN`).
- No RFC 9728 Protected Resource Metadata (PRM).
- No per-agent audit trail (`sub` identity).
- Fail-open when token unset (dev warning only).

## Solution

- FastMCP native OAuth RS: `token_verifier` + `AuthSettings` + `mcp.run(transport="streamable-http")`.
- LIME JWT verification via `lime-mcp-server-sdk`.
- New `auth/` package: settings, verifier adapter, agent context, factory.
- Per-tool structured logging with `agent_id` (JWT `sub`, never raw JWT).

## Breaking changes

- `MCP_HTTP_AUTH_TOKEN` deprecated; production uses `MCP_AUTH_MODE=lime`.
- `MCP_RESOURCE_SERVER_URL` required in lime mode.
- Legacy mode kept for one release (`http_auth_legacy.py`).

## Test plan

- [x] `pytest tests/ -v` — full matrix in `docs/AUTH_TEST_MATRIX.md`
- [x] PRM: `GET /.well-known/oauth-protected-resource`
- [x] 401 without token + invalid JWT
- [x] 200 with mock JWKS-signed JWT
- [x] Legacy bearer middleware
- [ ] `./scripts/smoke_lime_http.sh` (manual)
- [ ] Staging E2E with `lime-agents-sdk` (optional, not CI blocker)

## Production deploy checklist

```bash
MCP_AUTH_MODE=lime
MCP_RESOURCE_SERVER_URL=https://mcp.byteask.ai
MCP_ALLOWED_HOSTS=mcp.byteask.ai
LIME_BASE_URL=https://lime.pics
LIME_OAUTH_AUDIENCE=mcp
```

## Agent documentation

See `docs/AUTH.md` — two integration paths:

1. **SDK** (`lime-agents-sdk`): `list_tools` / `call_tool`
2. **Manual**: `get_mcp_access_token()` + `Authorization: Bearer`

## Files changed

| Area | Files |
|------|-------|
| Auth module | `src/byteask_embedded_mcp/auth/*` |
| Server factory | `server.py`, `config.py` |
| HTTP transport | `http_auth.py`, `http_auth_legacy.py` |
| Observability | `obs.py` (agent_id in document requests) |
| Tests | `tests/test_auth.py` |
| Docs | `docs/AUTH*.md`, `README.md`, `.env.example`, `server.json` |

## Non-goals (follow-up PRs)

- Rate limits / billing per agent
- Per-agent corpus ACL
- Human browser OAuth
- Removing legacy mode (next release)
