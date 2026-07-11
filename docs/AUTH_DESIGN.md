# ByteAsk Embedded MCP — Authentication Design

## Problem

The HTTP transport previously used a shared static bearer token (`MCP_HTTP_AUTH_TOKEN`).
That pattern:

- Cannot identify individual agents (no audit trail per caller).
- Cannot rotate credentials per agent without rotating for everyone.
- Does not expose RFC 9728 Protected Resource Metadata (PRM).
- Does not integrate with MCP OAuth 2.1 client discovery (401 + `WWW-Authenticate`).

## Solution

Use **FastMCP native OAuth resource-server mode** with **LIME** as the authorization server:

| Component | Role |
|-----------|------|
| LIME OAuth AS | Issues short-lived MCP JWTs (`aud=mcp`, `sub=agent_id`) via M2M token exchange |
| `lime-mcp-server-sdk` | Verifies Bearer JWT on the RS via JWKS |
| FastMCP `token_verifier` + `AuthSettings` | PRM, RequireAuthMiddleware, AuthContextMiddleware |

## LIME is M2M-only (non-standard OAuth)

LIME does **not** use browser redirects or authorization_code for agents.

```
Agent                          LIME AS                         ByteAsk RS
  | POST /modules/oauth/token      |                                |
  | X-Agent-Token: at_...          |                                |
  | (empty body)                   |                                |
  |<--------- MCP JWT -------------|                                |
  | POST /mcp Authorization: Bearer JWT ---------------------------->|
  |                                |                    JWKS verify |
  |<----------------------------- tool response -------------------|
```

Human browser OAuth and site passport (`lime-site-login`) are **out of scope** for this server.

## Auth modes

| `MCP_AUTH_MODE` | Use case | Production |
|-----------------|----------|------------|
| `lime` | LIME JWT verification | **Yes** |
| `legacy` | Static `MCP_HTTP_AUTH_TOKEN` | Deprecated (1 release) |
| `none` | Open HTTP | Dev only |

## Fail-closed rules

- `MCP_AUTH_MODE=lime` requires `MCP_RESOURCE_SERVER_URL` at startup.
- `MCP_AUTH_MODE=legacy` requires non-empty `MCP_HTTP_AUTH_TOKEN`.
- Production hosted deploy must use `lime` + `MCP_ALLOWED_HOSTS=mcp.byteask.ai`.
- Never log raw JWTs; log `agent_id` (`sub`) only.

## Agent identity

JWT claim `sub` is the agent UUID (ADR 0083). Tools read it via `current_agent_id()`
backed by FastMCP `get_access_token()`.

## Future extensions (not in this PR)

- Per-agent rate limits and quotas keyed by `agent_id`.
- Subscription tiers.
- Per-agent corpus ACL in the private backend.

## References

- LIME ADR 0081 — OAuth module for MCP
- LIME ADR 0083 — `lime-mcp-server-sdk`
- RFC 9728 — OAuth Protected Resource Metadata
