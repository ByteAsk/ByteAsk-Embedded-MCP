"""Auth contract tests — ZTA matrix from docs/AUTH_TEST_MATRIX.md."""

from __future__ import annotations

import json
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from lime_mcp_server import TokenVerifier
from mcp.server.auth.settings import AuthSettings as McpAuthSettings
from mcp.server.fastmcp import FastMCP
from starlette.testclient import TestClient

from byteask_embedded_mcp.auth import AuthConfig, build_mcp, current_agent_id
from byteask_embedded_mcp.auth.factory import transport_security
from byteask_embedded_mcp.auth.lime_verifier import LimeMcpTokenVerifier
from byteask_embedded_mcp.config import Config
from byteask_embedded_mcp.http_auth_legacy import BearerTokenMiddleware
from byteask_embedded_mcp.server import SERVER_INSTRUCTIONS, SERVER_NAME, register_tools

TEST_AGENT_ID = "agent-test-uuid"
TEST_ISSUER = "http://testserver"
TEST_RESOURCE = "http://127.0.0.1:8000"


class StaticJwksCache:
    """Minimal JWKS cache stub backed by pre-fetched contract keys."""

    def __init__(self, keys: list[dict[str, Any]], issuer: str) -> None:
        self._keys = keys
        self._issuer = issuer

    def warm(self) -> None:
        return None

    def close(self) -> None:
        return None

    def refresh(self, *, force: bool = False) -> None:
        return None

    def invalidate(self) -> None:
        return None

    def get_jwks(self, _kid: str | None) -> tuple[list[dict[str, Any]], str]:
        return self._keys, self._issuer


def _test_config() -> Config:
    root = Config.load().root
    return Config(
        root=root,
        log_dir=root / "logs",
        http_host="127.0.0.1",
        http_port=8000,
    )


def _build_rsa_signer() -> tuple[bytes, dict[str, Any], str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(public_key)
    jwk_dict = json.loads(jwk) if isinstance(jwk, str) else dict(jwk)
    kid = "byteask-test-kid"
    jwk_dict["kid"] = kid
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem, jwk_dict, kid


def _sign_mcp_jwt(
    pem: bytes,
    *,
    kid: str,
    sub: str = TEST_AGENT_ID,
    issuer: str = TEST_ISSUER,
) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": sub,
            "aud": "mcp",
            "iss": issuer,
            "iat": now,
            "exp": now + 300,
        },
        pem,
        algorithm="RS256",
        headers={"kid": kid},
    )


def _mcp_initialize_payload() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "contract-test", "version": "1.0"},
        },
    }


def _build_lime_mcp(*, jwks_keys: list[dict[str, Any]], issuer: str = TEST_ISSUER) -> FastMCP:
    cache = StaticJwksCache(jwks_keys, issuer)
    verifier = TokenVerifier(cache=cache)
    auth = AuthConfig(
        mode="lime",
        lime_base_url=issuer,
        lime_oauth_audience="mcp",
        resource_server_url=TEST_RESOURCE,
        legacy_token="",
    )
    config = _test_config()
    mcp = FastMCP(
        SERVER_NAME,
        host=config.http_host,
        port=config.http_port,
        streamable_http_path="/mcp",
        instructions=SERVER_INSTRUCTIONS,
        token_verifier=LimeMcpTokenVerifier(verifier=verifier),
        auth=McpAuthSettings(
            issuer_url=issuer,
            resource_server_url=TEST_RESOURCE,
        ),
        transport_security=transport_security(),
    )
    register_tools(mcp)
    return mcp


@pytest.fixture
def rsa_signer():
    return _build_rsa_signer()


@pytest.fixture
def lime_mcp_app(rsa_signer):
    _pem, jwk_dict, _kid = rsa_signer
    mcp = _build_lime_mcp(jwks_keys=[jwk_dict])
    return mcp.streamable_http_app()


def test_auth_config_lime_requires_resource_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_AUTH_MODE", "lime")
    monkeypatch.delenv("MCP_RESOURCE_SERVER_URL", raising=False)
    with pytest.raises(ValueError, match="MCP_RESOURCE_SERVER_URL"):
        AuthConfig.load()


def test_auth_config_legacy_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_AUTH_MODE", "legacy")
    monkeypatch.delenv("MCP_HTTP_AUTH_TOKEN", raising=False)
    with pytest.raises(ValueError, match="MCP_HTTP_AUTH_TOKEN"):
        AuthConfig.load()


@pytest.mark.asyncio
async def test_prm_endpoint(lime_mcp_app) -> None:
    transport = ASGITransport(app=lime_mcp_app)
    async with AsyncClient(transport=transport, base_url=TEST_RESOURCE) as client:
        response = await client.get("/.well-known/oauth-protected-resource")
    assert response.status_code == 200
    body = response.json()
    servers = [s.rstrip("/") for s in body.get("authorization_servers", [])]
    assert TEST_ISSUER.rstrip("/") in servers


@pytest.mark.asyncio
async def test_mcp_401_no_token(lime_mcp_app) -> None:
    transport = ASGITransport(app=lime_mcp_app)
    async with AsyncClient(transport=transport, base_url=TEST_RESOURCE) as client:
        response = await client.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json=_mcp_initialize_payload(),
        )
    assert response.status_code == 401
    assert "resource_metadata" in response.headers.get("www-authenticate", "").lower()


@pytest.mark.asyncio
async def test_mcp_401_invalid_jwt(lime_mcp_app) -> None:
    transport = ASGITransport(app=lime_mcp_app)
    async with AsyncClient(transport=transport, base_url=TEST_RESOURCE) as client:
        response = await client.post(
            "/mcp",
            headers={
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer invalid",
            },
            json=_mcp_initialize_payload(),
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mcp_200_valid_jwt(lime_mcp_app, rsa_signer) -> None:
    pem, _jwk, kid = rsa_signer
    token = _sign_mcp_jwt(pem, kid=kid)
    with TestClient(lime_mcp_app, base_url=TEST_RESOURCE) as client:
        response = client.post(
            "/mcp",
            headers={
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {token}",
            },
            json=_mcp_initialize_payload(),
        )
    assert response.status_code == 200


def test_legacy_bearer_middleware() -> None:
    auth = AuthConfig(
        mode="none",
        lime_base_url=TEST_ISSUER,
        lime_oauth_audience="mcp",
        resource_server_url="",
        legacy_token="",
    )
    mcp = build_mcp(
        auth=auth,
        config=_test_config(),
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
    )
    register_tools(mcp)
    app = BearerTokenMiddleware(mcp.streamable_http_app(), "legacy-secret")
    with TestClient(app, base_url=TEST_RESOURCE) as client:
        bad = client.post(
            "/mcp",
            headers={
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer wrong",
            },
            json=_mcp_initialize_payload(),
        )
        ok = client.post(
            "/mcp",
            headers={
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer legacy-secret",
            },
            json=_mcp_initialize_payload(),
        )
    assert bad.status_code == 401
    assert ok.status_code != 401


def test_stdio_build_has_no_verifier() -> None:
    auth = AuthConfig(
        mode="none",
        lime_base_url=TEST_ISSUER,
        lime_oauth_audience="mcp",
        resource_server_url="",
        legacy_token="",
    )
    mcp = build_mcp(
        auth=auth,
        config=_test_config(),
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
    )
    assert getattr(mcp, "token_verifier", None) is None


def test_current_agent_id_without_context() -> None:
    assert current_agent_id() is None


def test_current_agent_id_with_mock_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp.server.auth.provider import AccessToken

    monkeypatch.setattr(
        "byteask_embedded_mcp.auth.agent_context.get_access_token",
        lambda: AccessToken(
            token="x",
            client_id=TEST_AGENT_ID,
            scopes=[],
            subject=TEST_AGENT_ID,
            claims={"sub": TEST_AGENT_ID},
        ),
    )
    assert current_agent_id() == TEST_AGENT_ID


def test_none_mode_http_unauthenticated() -> None:
    auth = AuthConfig(
        mode="none",
        lime_base_url=TEST_ISSUER,
        lime_oauth_audience="mcp",
        resource_server_url="",
        legacy_token="",
    )
    mcp = build_mcp(
        auth=auth,
        config=_test_config(),
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
    )
    register_tools(mcp)
    with TestClient(mcp.streamable_http_app(), base_url=TEST_RESOURCE) as client:
        response = client.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json=_mcp_initialize_payload(),
        )
    assert response.status_code != 401
    assert response.status_code < 500
