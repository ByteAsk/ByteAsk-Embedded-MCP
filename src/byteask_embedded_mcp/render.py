"""Render structured retrieval results as compact markdown text.

Mirrors popular documentation-search MCP servers: markdown text, one hit =
document title + section/page citation + verbatim snippet (as a blockquote) + a
result_id handle for get_context. No scores, no per-doc labels — every document
is treated equally.
"""

from __future__ import annotations


def _page_str(page, page_end) -> str:
    if not page:
        return ""
    if page_end and page_end != page:
        return f"pp.{page}–{page_end}"
    return f"p.{page}"


def _citation(section: str, page, page_end) -> str:
    bits: list[str] = []
    sec = (section or "").strip()
    if sec and sec.split()[0] != "0":  # skip a synthetic "0 Front Matter" section
        bits.append(f"§{sec}")
    pg = _page_str(page, page_end)
    if pg:
        bits.append(pg)
    return ", ".join(bits)


def _blockquote(text: str) -> list[str]:
    return [f"> {ln}" if ln.strip() else ">" for ln in (text or "").splitlines()]


def render_search(result: dict) -> str:
    """Render a backend ``search()`` result as markdown."""
    query = result.get("query", "")
    hits = result.get("results", [])
    status = result.get("status", "ok")

    lines = [f'## Results for "{query}"', ""]
    if status != "ok":
        lines.append(
            "_No confident match in the indexed corpus — treat as not found; "
            "do not fabricate an answer._"
        )
        if not hits:
            return "\n".join(lines).rstrip()
        lines.append("")

    for h in hits:
        title = h.get("doc_title") or h.get("doc_id") or "(untitled)"
        cite = _citation(h.get("section", ""), h.get("page"), h.get("page_end"))
        header = f"### {title}" + (f" — {cite}" if cite else "")
        lines.append(header)
        lines.extend(_blockquote((h.get("snippet") or "").strip()))
        rid = h.get("result_id", "")
        if rid:
            lines.append(f"_ref: {rid}_")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_context(result: dict) -> str:
    """Render a backend ``get_context()`` result as markdown."""
    if result.get("status") != "ok":
        return f"_Not found: {result.get('result_id', '')}_"
    title = result.get("doc_title", "")
    cite = _citation(result.get("section", ""), result.get("page_start"),
                     result.get("page_end"))
    head = f"## {title}" + (f" — {cite}" if cite else "")
    return head + "\n\n" + (result.get("text") or "").strip()
