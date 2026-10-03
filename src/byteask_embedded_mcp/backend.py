"""Pluggable search backend — the seam between this server and retrieval.

The MCP server (``server.py``) is backend-agnostic: it depends only on the small
:class:`SearchBackend` interface below — two methods that return plain dicts.
Everything about *how* documents are parsed, chunked, embedded, ranked, or stored
lives behind this seam and is intentionally **not** part of this open-source repo.
The hosted ByteAsk endpoint plugs in a private backend over a licensed corpus.

Out of the box the server uses :class:`SampleBackend`, an in-memory stub over a
handful of illustrative, public-knowledge records, so you can clone, run, and
connect a client in one minute. To wire your own retrieval, implement
:class:`SearchBackend` and point ``BYTEASK_BACKEND`` at a factory:

    BYTEASK_BACKEND="my_pkg.my_module:make_backend"

where ``make_backend(config) -> SearchBackend``.

Return-value contracts
-----------------------
``search(query, limit, effort)`` -> ::

    {
      "status": "ok" | "no_match",
      "query":  str,
      "count":  int,
      "results": [ {result_id, doc_title, section, page, page_end, snippet}, ... ],
    }

``get_context(result_id, effort)`` -> ::

    {
      "status": "ok" | "not_found",
      "result_id": str,
      # present only when status == "ok":
      "doc_title": str, "section": str,
      "page_start": int, "page_end": int, "text": str,
    }
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .schemas import Hit, Section


@runtime_checkable
class SearchBackend(Protocol):
    """The contract the MCP server depends on. Implement these two methods."""

    def search(self, query: str, limit: int = 8, effort: str | None = None) -> dict:
        """Return ranked, verbatim evidence for a query (see module docstring)."""
        ...

    def get_context(self, result_id: str, effort: str | None = None) -> dict:
        """Expand a previous hit to its full source section (see module docstring)."""
        ...


# --------------------------------------------------------------------------- #
# SampleBackend — a tiny, dependency-free stub so the server runs immediately.
#
# The records below are short, well-known, public-domain facts (a Modbus
# function code; the Cortex-M SysTick control register) written from scratch as
# illustrations. They are NOT drawn from any licensed corpus and exist only to
# demonstrate the response shape. Swap in a real SearchBackend for production.
# --------------------------------------------------------------------------- #


@dataclass
class _SampleDoc:
    result_id: str
    doc_title: str
    section: str
    page: int
    page_end: int
    snippet: str
    context: str
    keywords: list[str] = field(default_factory=list)


_SAMPLE_DOCS: list[_SampleDoc] = [
    _SampleDoc(
        result_id="sample:modbus-fc16",
        doc_title="Sample — Modbus Application Protocol (illustrative)",
        section="6.12",
        page=30,
        page_end=30,
        snippet=(
            "Function code 16 (0x10), Write Multiple Registers, writes a block of "
            "contiguous holding registers (1 to 123 registers) in a remote device. "
            "The request specifies the starting address, the quantity of registers, "
            "the byte count, and the register values."
        ),
        context=(
            "Function code 16 (0x10), Write Multiple Registers, writes a block of "
            "contiguous holding registers (1 to 123 registers) in a remote device.\n\n"
            "Request: starting address (2 bytes), quantity of registers (2 bytes), "
            "byte count (1 byte), then the register values (2 bytes each).\n\n"
            "Normal response: the function code, the starting address, and the "
            "quantity of registers written. This is illustrative sample text, not a "
            "quotation from any specification."
        ),
        keywords=["modbus", "function", "code", "16", "0x10", "write", "multiple",
                  "registers", "holding", "fc16"],
    ),
    _SampleDoc(
        result_id="sample:cortex-m-systick",
        doc_title="Sample — Arm Cortex-M SysTick (illustrative)",
        section="SYST_CSR",
        page=4,
        page_end=4,
        snippet=(
            "The SysTick Control and Status Register (SYST_CSR) enables the SysTick "
            "features. Bit 0 (ENABLE) starts the counter; bit 1 (TICKINT) enables the "
            "SysTick exception request; bit 2 (CLKSOURCE) selects the clock source; "
            "bit 16 (COUNTFLAG) reads as 1 if the timer reached zero since last read."
        ),
        context=(
            "SysTick Control and Status Register (SYST_CSR).\n\n"
            "ENABLE (bit 0): 0 = counter disabled, 1 = counter enabled.\n"
            "TICKINT (bit 1): 1 = assert the SysTick exception on count to zero.\n"
            "CLKSOURCE (bit 2): 0 = external reference clock, 1 = processor clock.\n"
            "COUNTFLAG (bit 16): set to 1 when the counter counts down to zero; "
            "cleared by reading the register. Illustrative sample text only."
        ),
        keywords=["cortex", "systick", "syst_csr", "register", "enable", "tickint",
                  "clksource", "countflag", "arm", "timer", "bit"],
    ),
]


class SampleBackend:
    """In-memory stub backend over a few illustrative records.

    Scores documents by simple keyword overlap with the query. Returns
    ``no_match`` when nothing overlaps — mirroring the production contract that
    the server must never fabricate an answer.
    """

    def __init__(self, docs: list[_SampleDoc] | None = None) -> None:
        self._docs = docs if docs is not None else _SAMPLE_DOCS
        self._by_id = {d.result_id: d for d in self._docs}

    @staticmethod
    def _tokens(text: str) -> set[str]:
        words = "".join(
            c.lower() if (c.isalnum() or c == "_") else " " for c in text
        ).split()
        tokens = set(words)
        for w in words:
            if "_" in w:
                tokens.update(part for part in w.split("_") if part)
        return tokens

    def search(self, query: str, limit: int = 8, effort: str | None = None) -> dict:
        q = self._tokens(query)
        scored: list[tuple[int, _SampleDoc]] = []
        for d in self._docs:
            kw = {t for k in d.keywords for t in self._tokens(k)}
            score = len(q & kw)
            if score > 0:
                scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)

        hits = [
            Hit(
                result_id=d.result_id,
                doc_title=d.doc_title,
                section=d.section,
                page=d.page,
                page_end=d.page_end,
                snippet=d.snippet,
            ).to_dict()
            for _, d in scored[: max(1, limit)]
        ]
        status = "ok" if hits else "no_match"
        return {"status": status, "query": query, "count": len(hits), "results": hits}

    def get_context(self, result_id: str, effort: str | None = None) -> dict:
        d = self._by_id.get(result_id)
        if d is None:
            return {"status": "not_found", "result_id": result_id}
        return Section(
            result_id=d.result_id,
            doc_title=d.doc_title,
            section=d.section,
            page_start=d.page,
            page_end=d.page_end,
            text=d.context,
        ).to_dict() | {"status": "ok"}


def load_backend(config) -> SearchBackend:
    """Resolve the configured backend, or the bundled :class:`SampleBackend`.

    ``config.backend_factory`` is a dotted ``"module:callable"`` string; the
    callable is invoked with ``config`` and must return a :class:`SearchBackend`.
    Empty -> :class:`SampleBackend`.
    """
    spec = (getattr(config, "backend_factory", "") or "").strip()
    if not spec:
        return SampleBackend()
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise ValueError(
            f"BYTEASK_BACKEND must be 'module:callable', got {spec!r}"
        )
    factory = getattr(importlib.import_module(module_name), attr)
    return factory(config)
