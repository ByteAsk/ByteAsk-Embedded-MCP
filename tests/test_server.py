"""Server-level tests: tool wrappers and document-request logging."""

from byteask_embedded_mcp import server
from byteask_embedded_mcp.obs import JsonlWriter


def test_search_docs_tool_returns_markdown():
    out = server.search_docs("modbus write multiple registers")
    assert "## Results for" in out
    assert "_ref:" in out


def test_get_context_tool_expands_hit():
    # Drive through the same backend the tool uses.
    rid = server._svc().search("systick")["results"][0]["result_id"]
    out = server.get_context(rid)
    assert out.startswith("## ")


def test_request_document_empty_is_rejected():
    msg = server._do_request_document("   ")
    assert "could not file an empty request" in msg


def test_request_document_logs(tmp_path, monkeypatch):
    log = tmp_path / "document_requests.jsonl"
    monkeypatch.setattr(server, "_doc_requests", JsonlWriter(log))
    msg = server._do_request_document("IEEE 1547-2018, ride-through thresholds")
    assert "Request received" in msg
    assert log.exists() and "IEEE 1547-2018" in log.read_text()
