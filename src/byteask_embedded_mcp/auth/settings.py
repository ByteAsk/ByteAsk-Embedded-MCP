"""Authentication configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

AuthMode = Literal["none", "legacy", "lime"]


def _env(name: str, default: str = "") -> str:
    val = os.getenv(name)
    return val.strip() if val is not None and val.strip() != "" else default


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(_project_root() / ".env", override=False)
    except Exception:
        pass


@dataclass(frozen=True)
class AuthConfig:
    """Resolved auth settings. Construct via :meth:`load` or directly in tests."""

    mode: AuthMode
    lime_base_url: str
    lime_oauth_audience: str
    resource_server_url: str
    legacy_token: str

    @classmethod
    def load(cls) -> AuthConfig:
        _load_dotenv()
        mode_raw = _env("MCP_AUTH_MODE", "none").lower()
        if mode_raw not in ("none", "legacy", "lime"):
            raise ValueError(
                f"MCP_AUTH_MODE must be none, legacy, or lime (got {mode_raw!r})"
            )
        mode: AuthMode = mode_raw  # type: ignore[assignment]

        lime_base_url = _env("LIME_BASE_URL", "https://lime.pics")
        lime_oauth_audience = _env("LIME_OAUTH_AUDIENCE", "mcp")
        resource_server_url = _env("MCP_RESOURCE_SERVER_URL", "")
        legacy_token = _env("MCP_HTTP_AUTH_TOKEN", "")

        if mode == "lime" and not resource_server_url:
            raise ValueError(
                "MCP_AUTH_MODE=lime requires MCP_RESOURCE_SERVER_URL "
                "(public URL of this MCP resource server)"
            )
        if mode == "legacy" and not legacy_token:
            raise ValueError(
                "MCP_AUTH_MODE=legacy requires MCP_HTTP_AUTH_TOKEN "
                "(deprecated — migrate to MCP_AUTH_MODE=lime)"
            )

        return cls(
            mode=mode,
            lime_base_url=lime_base_url,
            lime_oauth_audience=lime_oauth_audience,
            resource_server_url=resource_server_url,
            legacy_token=legacy_token,
        )
