from __future__ import annotations

import base64
import io
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

import pytest

from scripts.acr_oauth_docker_login import (
    docker_login,
    exchange_refresh_token,
    validate_authenticated_publisher_token,
)


class _FakeResponse:
    def __init__(self, payload: Mapping[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def _jwt(payload: Mapping[str, object]) -> str:
    def encode(value: Mapping[str, object]) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode(payload)}.signature"


def test_exchange_refresh_token_posts_only_to_expected_acr_oauth_endpoint() -> None:
    captured: dict[str, object] = {}
    refresh_token = "r" * 64

    def _urlopen(request: urllib.request.Request, *, timeout: int) -> _FakeResponse:
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["content_type"] = request.headers["Content-type"]
        captured["timeout"] = timeout
        captured["body"] = urllib.parse.parse_qs((request.data or b"").decode("utf-8"))
        return _FakeResponse({"refresh_token": refresh_token})

    result = exchange_refresh_token(
        registry_server="example.azurecr.io",
        tenant_id="tenant-test",
        aad_access_token="a" * 64,
        urlopen=_urlopen,
    )

    assert result == refresh_token
    assert captured == {
        "url": "https://example.azurecr.io/oauth2/exchange",
        "method": "POST",
        "content_type": "application/x-www-form-urlencoded",
        "timeout": 30,
        "body": {
            "grant_type": ["access_token"],
            "service": ["example.azurecr.io"],
            "tenant": ["tenant-test"],
            "access_token": ["a" * 64],
        },
    }


@pytest.mark.parametrize(
    ("registry_server", "tenant_id", "access_token"),
    [
        ("", "tenant", "a" * 64),
        ("https://example.azurecr.io", "tenant", "a" * 64),
        ("example.azurecr.io/path", "tenant", "a" * 64),
        ("example.azurecr.io", "", "a" * 64),
        ("example.azurecr.io", "tenant", ""),
    ],
)
def test_exchange_refresh_token_rejects_malformed_inputs(
    registry_server: str,
    tenant_id: str,
    access_token: str,
) -> None:
    with pytest.raises(ValueError):
        exchange_refresh_token(
            registry_server=registry_server,
            tenant_id=tenant_id,
            aad_access_token=access_token,
        )


def test_exchange_refresh_token_fails_closed_when_exchange_returns_no_usable_token() -> None:
    def _urlopen(request: urllib.request.Request, *, timeout: int) -> _FakeResponse:
        del request, timeout
        return _FakeResponse({"refresh_token": "short"})

    with pytest.raises(RuntimeError, match="usable refresh token"):
        exchange_refresh_token(
            registry_server="example.azurecr.io",
            tenant_id="tenant-test",
            aad_access_token="a" * 64,
            urlopen=_urlopen,
        )


def test_exchange_refresh_token_surfaces_only_sanitized_acr_error_code() -> None:
    secret_marker = "do-not-log-this-response-message"

    def _urlopen(request: urllib.request.Request, *, timeout: int) -> _FakeResponse:
        del timeout
        body = json.dumps(
            {"errors": [{"code": "DENIED", "message": secret_marker}]}
        ).encode("utf-8")
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "Forbidden",
            hdrs=None,
            fp=io.BytesIO(body),
        )

    with pytest.raises(RuntimeError) as exc_info:
        exchange_refresh_token(
            registry_server="example.azurecr.io",
            tenant_id="tenant-test",
            aad_access_token="sensitive-token-value",
            urlopen=_urlopen,
        )

    message = str(exc_info.value)
    assert "HTTP 403" in message
    assert "code=DENIED" in message
    assert secret_marker not in message
    assert "sensitive-token-value" not in message


def test_validate_authenticated_publisher_token_defers_rbac_to_bootstrap() -> None:
    principal_id = "11111111-2222-3333-4444-555555555555"
    token = _jwt({"oid": principal_id, "tid": "tenant-test"})

    evidence = validate_authenticated_publisher_token(
        aad_access_token=token,
        tenant_id="TENANT-TEST",
        role_assignment_mode="LegacyRegistryPermissions",
    )

    assert evidence["expected_writer_role"] == "AcrPush"
    assert evidence["token_identity_claims_verified"] is True
    assert evidence["token_tenant_verified"] is True
    assert evidence["control_plane_rbac_verification"] == "bootstrap_operator_boundary"
    assert evidence["runtime_rbac_enumeration_performed"] is False
    assert evidence["acr_oauth_exchange_verified"] is False
    assert evidence["docker_login_verified"] is False
    assert evidence["effective_push_verified"] is False
    assert principal_id not in json.dumps(evidence)


def test_validate_authenticated_publisher_token_rejects_wrong_tenant() -> None:
    token = _jwt(
        {
            "oid": "11111111-2222-3333-4444-555555555555",
            "tid": "tenant-a",
        }
    )
    with pytest.raises(RuntimeError, match="tenant does not match"):
        validate_authenticated_publisher_token(
            aad_access_token=token,
            tenant_id="tenant-b",
            role_assignment_mode="LegacyRegistryPermissions",
        )


def test_validate_authenticated_publisher_token_rejects_unknown_role_mode() -> None:
    token = _jwt(
        {
            "oid": "11111111-2222-3333-4444-555555555555",
            "tid": "tenant-test",
        }
    )
    with pytest.raises(RuntimeError, match="Unsupported ACR role-assignment mode"):
        validate_authenticated_publisher_token(
            aad_access_token=token,
            tenant_id="tenant-test",
            role_assignment_mode="unexpected",
        )


def test_docker_login_passes_refresh_token_only_over_stdin() -> None:
    captured: dict[str, Any] = {}
    refresh_token = "r" * 64

    def _runner(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured.update(kwargs)
        return subprocess.CompletedProcess(args=args, returncode=0)

    docker_login(
        registry_server="example.azurecr.io",
        refresh_token=refresh_token,
        runner=_runner,
    )

    assert captured["args"] == [
        "docker",
        "login",
        "example.azurecr.io",
        "--username",
        "00000000-0000-0000-0000-000000000000",
        "--password-stdin",
    ]
    assert refresh_token not in captured["args"]
    assert captured["input"] == refresh_token
    assert captured["text"] is True
    assert captured["check"] is True
    assert captured["stdout"] is subprocess.DEVNULL


def test_docker_login_rejects_short_refresh_token_before_subprocess() -> None:
    called = False

    def _runner(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal called
        del kwargs
        called = True
        return subprocess.CompletedProcess(args=args, returncode=0)

    with pytest.raises(ValueError, match="refresh_token"):
        docker_login(
            registry_server="example.azurecr.io",
            refresh_token="short",
            runner=_runner,
        )

    assert called is False
