#!/usr/bin/env python3
"""Authenticate Docker to Azure Container Registry without reusable registry credentials."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Protocol, cast

_DOCKER_TOKEN_USERNAME = "00000000-0000-0000-0000-000000000000"
_MIN_REFRESH_TOKEN_LENGTH = 32


class UrlResponse(Protocol):
    def __enter__(self) -> UrlResponse: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def read(self) -> bytes: ...


UrlOpen = Callable[..., UrlResponse]
DockerRunner = Callable[..., subprocess.CompletedProcess[str]]
_DEFAULT_URL_OPEN: UrlOpen = cast(UrlOpen, urllib.request.urlopen)
_DEFAULT_DOCKER_RUNNER: DockerRunner = cast(DockerRunner, subprocess.run)


def exchange_refresh_token(
    *,
    registry_server: str,
    tenant_id: str,
    aad_access_token: str,
    urlopen: UrlOpen = _DEFAULT_URL_OPEN,
) -> str:
    """Exchange an ACR-audience Entra token for a short-lived ACR refresh token."""
    server = registry_server.strip()
    tenant = tenant_id.strip()
    access_token = aad_access_token.strip()
    if not server or "/" in server or "://" in server:
        raise ValueError("registry_server must be an ACR login hostname")
    if not tenant:
        raise ValueError("tenant_id is required")
    if not access_token:
        raise ValueError("aad_access_token is required")

    payload = urllib.parse.urlencode(
        {
            "grant_type": "access_token",
            "service": server,
            "tenant": tenant,
            "access_token": access_token,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://{server}/oauth2/exchange",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        decoded = json.loads(response.read())
    if not isinstance(decoded, dict):
        raise RuntimeError("ACR OAuth exchange returned a non-object response")
    refresh_token = decoded.get("refresh_token")
    if not isinstance(refresh_token, str) or len(refresh_token) < _MIN_REFRESH_TOKEN_LENGTH:
        raise RuntimeError("ACR OAuth exchange did not return a usable refresh token")
    return refresh_token


def docker_login(
    *,
    registry_server: str,
    refresh_token: str,
    runner: DockerRunner = _DEFAULT_DOCKER_RUNNER,
) -> None:
    """Pass the ACR refresh token only over stdin to Docker login."""
    token = refresh_token.strip()
    if len(token) < _MIN_REFRESH_TOKEN_LENGTH:
        raise ValueError("refresh_token is not usable")
    runner(
        [
            "docker",
            "login",
            registry_server,
            "--username",
            _DOCKER_TOKEN_USERNAME,
            "--password-stdin",
        ],
        input=token,
        text=True,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def authenticate_from_environment() -> None:
    """Authenticate using short-lived values supplied only through process environment."""
    server = os.environ.get("REGISTRY_SERVER", "")
    tenant = os.environ.get("ACR_TENANT_ID", "")
    access_token = os.environ.get("ACR_AAD_ACCESS_TOKEN", "")
    refresh_token = exchange_refresh_token(
        registry_server=server,
        tenant_id=tenant,
        aad_access_token=access_token,
    )
    docker_login(registry_server=server, refresh_token=refresh_token)


if __name__ == "__main__":
    authenticate_from_environment()
