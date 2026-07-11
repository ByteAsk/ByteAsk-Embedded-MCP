"""Streamable HTTP transport entrypoint."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .auth.settings import AuthConfig
from .config import Config

logger = logging.getLogger("byteask_embedded_mcp")


def run_http(mcp: FastMCP, *, auth: AuthConfig, config: Config) -> None:
    """Serve Streamable HTTP with LIME OAuth RS, legacy bearer, or open dev mode."""
    if auth.mode == "legacy" and auth.legacy_token:
        import uvicorn

        from .http_auth_legacy import BearerTokenMiddleware

        logger.warning(
            "MCP_AUTH_MODE=legacy is deprecated — migrate to MCP_AUTH_MODE=lime"
        )
        app = BearerTokenMiddleware(mcp.streamable_http_app(), auth.legacy_token)
        logger.info(
            "Starting %s over Streamable HTTP (legacy bearer) at http://%s:%d/mcp",
            mcp.name,
            config.http_host,
            config.http_port,
        )
        uvicorn.run(
            app,
            host=config.http_host,
            port=config.http_port,
            log_level="warning",
        )
        return

    if auth.mode == "none":
        logger.warning(
            "MCP_AUTH_MODE=none — HTTP endpoint is UNAUTHENTICATED (dev only)"
        )
    elif auth.mode == "lime":
        logger.info("Auth mode: LIME (agent identity via JWKS)")

    logger.info(
        "Starting %s over Streamable HTTP at http://%s:%d/mcp",
        mcp.name,
        config.http_host,
        config.http_port,
    )
    mcp.run(transport="streamable-http")
