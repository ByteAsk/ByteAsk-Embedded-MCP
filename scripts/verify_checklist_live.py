"""Full verification checklist including live LIME JWT (requires LIME_AGENT_TOKEN env)."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

INIT_BODY = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "checklist", "version": "1.0"},
        },
    }
)
HEADERS = [
    "-H",
    "Accept: application/json, text/event-stream",
    "-H",
    "Content-Type: application/json",
]
MCP_URL = "http://127.0.0.1:8000/mcp"


def curl_status(*args: str) -> tuple[int, str]:
    cmd = ["curl.exe", "-s", "-o", "NUL", "-w", "%{http_code}", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    code = proc.stdout.strip() or "000"
    return int(code), proc.stderr.strip()


def curl_body(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["curl.exe", "-s", "-w", "\n%{http_code}", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    lines = proc.stdout.rsplit("\n", 1)
    if len(lines) == 2:
        return int(lines[1].strip()), lines[0]
    return 0, proc.stdout


def start_server(env: dict[str, str]) -> subprocess.Popen:
    merged = os.environ.copy()
    merged.update(env)
    if env.get("MCP_AUTH_MODE") != "lime":
        merged.pop("MCP_RESOURCE_SERVER_URL", None)
    log_path = ROOT / "logs" / "verify_server.log"
    log_path.parent.mkdir(exist_ok=True)
    log_fh = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(PYTHON), "-m", "byteask_embedded_mcp.server", "--transport", "http"],
        cwd=ROOT,
        env=merged,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    time.sleep(4)
    return proc


def stop_server(proc: subprocess.Popen) -> str:
    log_path = ROOT / "logs" / "verify_server.log"
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    return log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""


async def fetch_live_jwt() -> tuple[str | None, str | None]:
    token = os.environ.get("LIME_AGENT_TOKEN", "").strip()
    if not token:
        return None, "LIME_AGENT_TOKEN not set"
    from lime_agents import LimeAgent

    agent = LimeAgent(agent_token=token)
    try:
        result = await agent.get_mcp_access_token()
        return result.access_token, None
    except Exception as exc:
        return None, str(exc)
    finally:
        await agent.aclose()


async def _sdk_tool_checks() -> list[tuple[str, bool, str]]:
    """Use lime-agents-sdk against the already-running local lime RS."""
    token = os.environ.get("LIME_AGENT_TOKEN", "").strip()
    from lime_agents import LimeAgent

    agent = LimeAgent(agent_token=token)
    results: list[tuple[str, bool, str]] = []
    try:
        tools = await agent.list_tools(MCP_URL)
        names = [t.name for t in tools]
        results.append(("live: SDK list_tools succeeds", bool(tools), f"count={len(tools)}"))
        results.append(
            ("live: SDK list_tools includes search_docs", "search_docs" in names, str(names[:5]))
        )
        call = await agent.call_tool(MCP_URL, "search_docs", {"query": "modbus", "limit": 2})
        text = ""
        if call.content:
            for block in call.content:
                if hasattr(block, "text"):
                    text += block.text
        results.append(("live: SDK call_tool search_docs succeeds", not call.isError, text[:120] or "empty"))
        results.append(
            (
                "live: search_docs returned markdown",
                "## Results" in text or "no confident match" in text.lower(),
                "ok" if text else "empty",
            )
        )
    except Exception as exc:
        results.append(("live: SDK MCP session", False, str(exc)))
    finally:
        await agent.aclose()
    return results


def mcp_session_post(jwt: str, body: str) -> tuple[int, str]:
    return curl_body(
        "-X",
        "POST",
        *HEADERS,
        "-H",
        f"Authorization: Bearer {jwt}",
        "-d",
        body,
        MCP_URL,
    )


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    proc = start_server({"MCP_AUTH_MODE": "none"})
    status, _ = curl_status("-X", "POST", *HEADERS, "-d", INIT_BODY, MCP_URL)
    log = stop_server(proc)
    results.append(("none: POST /mcp without auth != 401", status != 401 and status < 500, f"status={status}"))
    results.append(("none: UNAUTHENTICATED warning", "UNAUTHENTICATED" in log, "ok"))

    proc = start_server({"MCP_AUTH_MODE": "legacy", "MCP_HTTP_AUTH_TOKEN": "test123"})
    ok_status, _ = curl_status(
        "-X", "POST", *HEADERS, "-H", "Authorization: Bearer test123", "-d", INIT_BODY, MCP_URL
    )
    bad_status, _ = curl_status(
        "-X", "POST", *HEADERS, "-H", "Authorization: Bearer wrong", "-d", INIT_BODY, MCP_URL
    )
    log = stop_server(proc)
    results.append(("legacy: valid bearer != 401", ok_status != 401, f"status={ok_status}"))
    results.append(("legacy: wrong bearer == 401", bad_status == 401, f"status={bad_status}"))
    results.append(("legacy: deprecated warning", "deprecated" in log.lower(), "ok"))

    proc = start_server(
        {
            "MCP_AUTH_MODE": "lime",
            "MCP_RESOURCE_SERVER_URL": "http://127.0.0.1:8000",
            "MCP_ALLOWED_HOSTS": "127.0.0.1,localhost",
        }
    )
    prm_status, prm_body = curl_body("http://127.0.0.1:8000/.well-known/oauth-protected-resource")
    prm_json = json.loads(prm_body) if prm_body.startswith("{") else {}
    servers = [s.rstrip("/") for s in prm_json.get("authorization_servers", [])]
    no_auth, _ = curl_status("-X", "POST", *HEADERS, "-d", INIT_BODY, MCP_URL)
    invalid, _ = curl_status(
        "-X",
        "POST",
        *HEADERS,
        "-H",
        "Authorization: Bearer invalid.jwt.token",
        "-d",
        INIT_BODY,
        MCP_URL,
    )

    jwt, jwt_err = asyncio.run(fetch_live_jwt())
    if jwt:
        init_status, _ = mcp_session_post(jwt, INIT_BODY)
        results.append(("live: obtain MCP JWT from LIME", True, f"jwt_len={len(jwt)}"))
        results.append(
            ("live: POST /mcp initialize with real JWT != 401", init_status != 401, f"status={init_status}")
        )
        results.extend(asyncio.run(_sdk_tool_checks()))
    else:
        results.append(("live: obtain MCP JWT from LIME", False, jwt_err or "missing token"))

    log = stop_server(proc)
    results.append(("lime: PRM 200", prm_status == 200, f"status={prm_status}"))
    results.append(
        ("lime: authorization_servers includes lime.pics", "https://lime.pics" in servers, str(servers))
    )
    results.append(("lime: no token -> 401", no_auth == 401, f"status={no_auth}"))
    results.append(("lime: invalid JWT -> 401", invalid == 401, f"status={invalid}"))
    results.append(("lime: LIME auth log line", "Auth mode: LIME" in log, "ok"))

    if jwt:
        agent_lines = [ln for ln in log.splitlines() if "tool=search_docs agent_id=" in ln]
        agent_ok = any(
            "agent_id=None" not in ln and "agent_id=" in ln and len(ln.split("agent_id=")[-1].strip()) > 4
            for ln in agent_lines
        )
        results.append(
            (
                "live: search_docs log contains agent_id (sub)",
                agent_ok,
                agent_lines[-1].strip() if agent_lines else log[-500:],
            )
        )
        jwt_accept = [ln for ln in log.splitlines() if "MCP JWT accepted sub=" in ln]
        sub = ""
        if jwt_accept:
            sub = jwt_accept[-1].split("sub=")[-1].strip()
        results.append(
            ("live: JWT verified sub= in server log", bool(jwt_accept), jwt_accept[-1].strip() if jwt_accept else "no line")
        )
        if sub and agent_lines:
            results.append(
                (
                    "live: agent_id matches JWT sub",
                    sub in agent_lines[-1],
                    f"sub={sub}",
                )
            )

    proc_pytest = subprocess.run(
        [str(PYTHON), "-m", "pytest", "tests/", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    results.append(
        (
            "pytest: all tests green",
            proc_pytest.returncode == 0 and "passed" in proc_pytest.stdout,
            proc_pytest.stdout.strip()[-80:],
        )
    )

    print("=== Full verification checklist (with live LIME JWT) ===")
    failed = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name} ({detail})")
        if not ok:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
