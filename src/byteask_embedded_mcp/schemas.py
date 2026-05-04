"""Lightweight result types shared by backends and the renderer.

Plain dataclasses (no Pydantic) to keep the dependency surface small. A backend
may return these or plain dicts of the same shape — the renderer and server only
read keys, never the types. Every document is treated equally: there is no
authority/trust metadata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Hit:
    """One piece of evidence: a verbatim snippet with a citation handle."""

    result_id: str          # opaque handle; pass to get_context to expand
    doc_title: str
    section: str
    page: int
    page_end: int
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Section:
    """A full source section, returned by get_context."""

    result_id: str
    doc_title: str
    section: str
    page_start: int
    page_end: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
