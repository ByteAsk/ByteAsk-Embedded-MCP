"""Deprecated shared-secret bearer guard for Streamable HTTP (one release)."""

from __future__ import annotations


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
