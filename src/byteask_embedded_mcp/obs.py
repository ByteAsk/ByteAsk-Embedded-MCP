"""Structured observability.

Tool calls are logged as one JSON line per event to ``logs/*.jsonl`` and
summarized to stderr. We never write to stdout: in stdio MCP mode stdout is the
JSON-RPC channel and must stay clean.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("byteask_embedded_mcp.query")

_lock = threading.Lock()


class JsonlWriter:
    """Append-only, timestamped, thread-safe JSONL sink.

    One append implementation shared by every log file (the query log and the
    document-request log), so each gets the same ``ts`` prefix, lock, and
    append-and-flush from a single place.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **record}
        line = json.dumps(record, ensure_ascii=False)
        with _lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return record


class QueryLogger:
    def __init__(self, log_dir: Path):
        self._writer = JsonlWriter(Path(log_dir) / "queries.jsonl")

    def log(self, record: dict[str, Any]) -> None:
        record = self._writer.append(record)
        # Compact stderr summary for live tailing.
        logger.info(
            "tool=%s query=%r status=%s n=%d latency_ms=%d",
            record.get("tool"),
            record.get("query"),
            record.get("status"),
            record.get("result_count", 0),
            int(record.get("latency_ms", 0)),
        )


def configure_stderr_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
