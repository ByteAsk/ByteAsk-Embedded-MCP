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


def test_server_startup_loads_dotenv(tmp_path):
    import os
    import subprocess
    import sys

    env_file = tmp_path / ".env"
    env_file.write_text(
        "MCP_TRANSPORT=http\n"
        "MCP_HTTP_AUTH_TOKEN=token_from_dotenv\n"
        "MCP_ALLOWED_HOSTS=mcp.example.com\n"
    )
    code = (
        "import os\n"
        "from byteask_embedded_mcp.server import mcp\n"
        "assert os.getenv('MCP_TRANSPORT') == 'http'\n"
        "assert os.getenv('MCP_HTTP_AUTH_TOKEN') == 'token_from_dotenv'\n"
        "assert 'mcp.example.com' in mcp.settings.transport_security.allowed_hosts\n"
    )
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("MCP_")}
    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=clean_env,
    )
    assert res.returncode == 0, res.stderr


