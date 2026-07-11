"""FastMCP token verifier adapter for LIME MCP JWTs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mcp.server.auth.provider import AccessToken

if TYPE_CHECKING:
    pass

logger = logging.getLogger("byteask_embedded_mcp.auth")


class LimeMcpTokenVerifier:
    """Verify LIME-issued MCP JWTs via ``lime-mcp-server-sdk`` ``TokenVerifier``."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        audience: str | None = None,
        verifier: Any | None = None,
    ) -> None:
        if verifier is not None:
            self._verifier = verifier
            return
        try:
            from lime_mcp_server import TokenVerifier
        except ImportError as exc:
            raise ImportError(
                "lime-mcp-server-sdk is required for MCP_AUTH_MODE=lime. "
                "Install with: uv sync"
            ) from exc
        self._verifier = TokenVerifier(base_url=base_url, audience=audience)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            result = await self._verifier.verify_async(token)
        except Exception:
            logger.debug("MCP JWT verification failed", exc_info=True)
            return None

        if not result.is_valid or result.claims is None:
            logger.debug("MCP JWT rejected: %s", result.error)
            return None

        subject = str(result.claims["sub"])
        logger.info("MCP JWT accepted sub=%s", subject)
        return AccessToken(
            token=token,
            client_id=subject,
            scopes=[],
            subject=subject,
            claims=dict(result.claims),
        )
