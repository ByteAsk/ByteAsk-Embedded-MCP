"""Streamable HTTP entrypoint with a stub bearer-token guard.

The MCP-spec-blessed path for HTTP auth is full OAuth 2.1 (FastMCP's
``token_verifier`` + ``AuthSettings``). That is overkill for many deployments, so
this module wraps the Streamable HTTP ASGI app with a minimal shared-secret
check: clients must send ``Authorization: Bearer <token>``.

Replace this stub with real auth (OAuth 2.1 resource server via ``AuthSettings``,
mTLS, or a trusted reverse proxy) before exposing publicly.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("byteask_embedded_mcp")


class BearerTokenMiddleware:
    """Pure-ASGI middleware requiring ``Authorization: Bearer <token>``.

    Non-HTTP scopes (e.g. the ASGI ``lifespan`` events that start the MCP session
    manager) pass straight through. Any HTTP request whose Authorization header
    does not match gets a 401 before it reaches the MCP application.
    """

    def __init__(self, app, token: str) -> None:
        self.app = app
        self._expected = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        if headers.get(b"authorization") == self._expected:
            await self.app(scope, receive, send)
            return

        await _send_401(send)


async def _send_401(send) -> None:
    """Emit a minimal JSON 401 response over raw ASGI."""
    body = b'{"error":"unauthorized","detail":"Missing or invalid bearer token."}'
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", b'Bearer realm="byteask-embedded-mcp"'),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def run_http(mcp: FastMCP, *, host: str, port: int, token: str) -> None:
    """Serve the Streamable HTTP transport, optionally guarded by a bearer token.

    Args:
        mcp: The configured FastMCP application.
        host: Bind address (use 0.0.0.0 to expose on the network).
        port: Bind port.
        token: Shared secret. If empty, the endpoint runs UNAUTHENTICATED and a
            loud warning is logged (intended for local development only).
    """
    import uvicorn  # local import keeps the stdio path free of the HTTP stack

    app = mcp.streamable_http_app()  # Starlette app; default route is /mcp

    if token:
        app = BearerTokenMiddleware(app, token)
        logger.info("HTTP bearer-token auth ENABLED.")
    else:
        logger.warning(
            "MCP_HTTP_AUTH_TOKEN is not set - the HTTP endpoint is UNAUTHENTICATED. "
            "Set a token before exposing this port (dev-only)."
        )

    logger.info("Starting byteask-embedded-mcp over Streamable HTTP at http://%s:%d/mcp",
                host, port)
    # uvicorn installs SIGINT/SIGTERM handlers and drains in-flight requests.
    uvicorn.run(app, host=host, port=port, log_level="warning")
