"""FastMCP construction with optional LIME OAuth resource-server auth."""

from __future__ import annotations

import os

from mcp.server.auth.settings import AuthSettings as McpAuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from ..config import Config
from .lime_verifier import LimeMcpTokenVerifier
from .settings import AuthConfig


def transport_security() -> TransportSecuritySettings:
    """DNS-rebinding protection from ``MCP_ALLOWED_HOSTS`` / ``MCP_ALLOWED_ORIGINS``."""
    raw_hosts = os.getenv("MCP_ALLOWED_HOSTS", "").strip()
    if raw_hosts == "*":
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    hosts = [h.strip() for h in raw_hosts.split(",") if h.strip()]
    hosts += ["127.0.0.1", "localhost", "127.0.0.1:*", "localhost:*"]

    raw_origins = os.getenv("MCP_ALLOWED_ORIGINS", "").strip()
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def build_mcp(
    *,
    auth: AuthConfig,
    config: Config,
    name: str,
    instructions: str,
) -> FastMCP:
    """Build a FastMCP instance. Auth kwargs are constructor-only (no import-time singleton)."""
    kwargs: dict = {
        "instructions": instructions,
        "transport_security": transport_security(),
    }

    if auth.mode == "lime":
        kwargs.update(
            host=config.http_host,
            port=config.http_port,
            streamable_http_path="/mcp",
            token_verifier=LimeMcpTokenVerifier(
                base_url=auth.lime_base_url,
                audience=auth.lime_oauth_audience,
            ),
            auth=McpAuthSettings(
                issuer_url=auth.lime_base_url,
                resource_server_url=auth.resource_server_url.rstrip("/"),
            ),
        )
    elif auth.mode in ("none", "legacy"):
        # Host/port required for streamable-http even without OAuth RS.
        kwargs.update(
            host=config.http_host,
            port=config.http_port,
            streamable_http_path="/mcp",
        )

    return FastMCP(name, **kwargs)
