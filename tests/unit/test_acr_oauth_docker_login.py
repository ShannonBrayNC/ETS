from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

import pytest

from scripts.acr_oauth_docker_login import docker_login, exchange_refresh_token


class _FakeResponse:
    def __init__(self, payload: Mapping[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


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
