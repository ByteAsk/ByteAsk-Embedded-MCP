"""Per-request agent identity from FastMCP auth context."""

from __future__ import annotations

from mcp.server.auth.middleware.auth_context import get_access_token


def current_agent_id() -> str | None:
    """Return the authenticated agent UUID (JWT ``sub``), or ``None`` if unauthenticated."""
    tok = get_access_token()
    if tok is None:
        return None
    return tok.subject or tok.client_id
