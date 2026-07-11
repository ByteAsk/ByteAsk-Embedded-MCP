# Auth Test Matrix (ZTA)

Normative acceptance criteria for ByteAsk Embedded MCP authentication.
Each row must have a corresponding automated test in `tests/test_auth.py`.

| ID | Mode | Transport | Request | Expected |
|----|------|-----------|---------|----------|
| A1 | `none` | HTTP | POST `/mcp` no Authorization | 200 or MCP protocol response (not 5xx) |
| A2 | `legacy` | HTTP | POST `/mcp` wrong bearer | 401 |
| A3 | `legacy` | HTTP | POST `/mcp` correct static token | MCP accepts (not 401) |
| A4 | `lime` | HTTP | GET `/.well-known/oauth-protected-resource` | 200, `authorization_servers` includes issuer |
| A5 | `lime` | HTTP | POST `/mcp` no Authorization | 401, `WWW-Authenticate` contains `resource_metadata` |
| A6 | `lime` | HTTP | POST `/mcp` Bearer `invalid` | 401 |
| A7 | `lime` | HTTP | POST `/mcp` valid JWT (mock JWKS) | Not 401 |
| A8 | `none` | stdio | N/A | No token_verifier on FastMCP instance |
| A9 | unit | N/A | `current_agent_id()` without auth context | `None` |
| A10 | unit | N/A | mock `get_access_token()` with subject | returns `sub` |

## Startup validation

| ID | Config | Expected |
|----|--------|----------|
| S1 | `MCP_AUTH_MODE=lime`, empty `MCP_RESOURCE_SERVER_URL` | Startup error |
| S2 | `MCP_AUTH_MODE=legacy`, empty `MCP_HTTP_AUTH_TOKEN` | Startup error |
