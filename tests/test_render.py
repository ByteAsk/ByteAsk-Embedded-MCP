"""Renderer unit tests — pure string formatting, no backend or network."""

from byteask_embedded_mcp.render import render_context, render_search


def test_render_search_ok():
    md = render_search({
        "status": "ok",
        "query": "write multiple registers",
        "results": [{
            "result_id": "sample:modbus-fc16",
            "doc_title": "Sample — Modbus",
            "section": "6.12",
            "page": 30,
            "page_end": 30,
            "snippet": "Function code 16 (0x10) ...",
        }],
    })
    assert '## Results for "write multiple registers"' in md
    assert "### Sample — Modbus — §6.12, p.30" in md
    assert "> Function code 16 (0x10) ..." in md
    assert "_ref: sample:modbus-fc16_" in md


def test_render_search_no_match():
    md = render_search({"status": "no_match", "query": "unrelated", "results": []})
    assert "No confident match" in md
    assert "do not fabricate" in md


def test_render_context_ok():
    md = render_context({
        "status": "ok",
        "doc_title": "Sample — Modbus",
        "section": "6.12",
        "page_start": 30,
        "page_end": 31,
        "text": "Full section text.",
    })
    assert md.startswith("## Sample — Modbus — §6.12, pp.30–31")
    assert "Full section text." in md


def test_render_context_not_found():
    md = render_context({"status": "not_found", "result_id": "nope"})
    assert md == "_Not found: nope_"
