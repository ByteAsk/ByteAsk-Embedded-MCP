"""Run verification checklist for auth modes (offline-friendly, no real LIME token)."""

from __future__ import annotations

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


def curl_status(*args: str) -> tuple[int, str]:
    cmd = ["curl.exe", "-s", "-o", "NUL", "-w", "%{http_code}", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    code = proc.stdout.strip() or "000"
    return int(code), proc.stderr.strip()


def curl_body(url: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["curl.exe", "-s", "-w", "\n%{http_code}", url],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    lines = proc.stdout.rsplit("\n", 1)
    if len(lines) == 2:
        body, status = lines[0], lines[1].strip()
        return int(status), body
    return 0, proc.stdout


def start_server(env: dict[str, str]) -> subprocess.Popen:
    merged = os.environ.copy()
    merged.update(env)
    merged.pop("MCP_RESOURCE_SERVER_URL", None) if env.get("MCP_AUTH_MODE") != "lime" else None
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
    time.sleep(3)
    return proc


def stop_server(proc: subprocess.Popen) -> str:
    log_path = ROOT / "logs" / "verify_server.log"
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    return log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    # 1. none mode
    proc = start_server({"MCP_AUTH_MODE": "none"})
    status, _ = curl_status("-X", "POST", *HEADERS, "-d", INIT_BODY, "http://127.0.0.1:8000/mcp")
    log = stop_server(proc)
    results.append(
        (
            "none: POST /mcp without auth != 401",
            status != 401 and status < 500,
            f"status={status}",
        )
    )
    results.append(
        (
            "none: UNAUTHENTICATED warning in log",
            "UNAUTHENTICATED" in log,
            "log snippet ok" if "UNAUTHENTICATED" in log else log[-500:],
        )
    )

    # 2. legacy mode
    proc = start_server({"MCP_AUTH_MODE": "legacy", "MCP_HTTP_AUTH_TOKEN": "test123"})
    ok_status, _ = curl_status(
        "-X",
        "POST",
        *HEADERS,
        "-H",
        "Authorization: Bearer test123",
        "-d",
        INIT_BODY,
        "http://127.0.0.1:8000/mcp",
    )
    bad_status, _ = curl_status(
        "-X",
        "POST",
        *HEADERS,
        "-H",
        "Authorization: Bearer wrong",
        "-d",
        INIT_BODY,
        "http://127.0.0.1:8000/mcp",
    )
    log = stop_server(proc)
    results.append(("legacy: valid bearer != 401", ok_status != 401, f"status={ok_status}"))
    results.append(("legacy: wrong bearer == 401", bad_status == 401, f"status={bad_status}"))
    results.append(
        (
            "legacy: deprecated warning",
            "deprecated" in log.lower(),
            "ok" if "deprecated" in log.lower() else log[-500:],
        )
    )

    # 3. lime mode
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
    no_auth, _ = curl_status("-X", "POST", *HEADERS, "-d", INIT_BODY, "http://127.0.0.1:8000/mcp")
    invalid, _ = curl_status(
        "-X",
        "POST",
        *HEADERS,
        "-H",
        "Authorization: Bearer invalid.jwt.token",
        "-d",
        INIT_BODY,
        "http://127.0.0.1:8000/mcp",
    )
    log = stop_server(proc)
    results.append(("lime: PRM 200", prm_status == 200, f"status={prm_status}"))
    results.append(
        (
            "lime: authorization_servers includes lime.pics",
            "https://lime.pics" in servers,
            str(servers),
        )
    )
    results.append(("lime: no token -> 401", no_auth == 401, f"status={no_auth}"))
    results.append(("lime: invalid JWT -> 401", invalid == 401, f"status={invalid}"))
    results.append(
        (
            "lime: LIME auth log line",
            "Auth mode: LIME" in log,
            "ok" if "Auth mode: LIME" in log else log[-500:],
        )
    )

    print("=== Verification checklist ===")
    failed = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name} ({detail})")
        if not ok:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
