"""Server configuration for byteask-embedded-mcp.

This is the *server's* config only — transport, logging, and which retrieval
backend to load. Anything about how documents are parsed, indexed, embedded, or
ranked lives behind the :class:`~byteask_embedded_mcp.backend.SearchBackend`
interface and is intentionally not part of this open-source server.

Values are overridable via environment variables (loaded from ``.env``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    val = os.getenv(name)
    return val if val is not None and val.strip() != "" else default


def _project_root() -> Path:
    # src/byteask_embedded_mcp/config.py -> project root is three parents up.
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    """Resolved server configuration. Construct via :meth:`load`."""

    root: Path
    log_dir: Path

    # Dotted "module:callable" returning a SearchBackend, called with this Config.
    # Empty -> the bundled in-memory SampleBackend. See backend.load_backend.
    backend_factory: str = ""

    @classmethod
    def load(cls) -> "Config":
        root = _project_root()
        # Best-effort load of the project .env so every entrypoint (CLI, server)
        # picks up the same settings. Real env vars take precedence.
        try:
            from dotenv import load_dotenv

            load_dotenv(root / ".env", override=False)
        except Exception:
            pass
        logs = Path(_env("BYTEASK_LOGS", str(root / "logs")))
        return cls(
            root=root,
            log_dir=logs if logs.is_absolute() else root / logs,
            backend_factory=_env("BYTEASK_BACKEND", ""),
        )
