#!/usr/bin/env python3
"""Authenticate Docker to Azure Container Registry without reusable registry credentials."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol, cast

_DOCKER_TOKEN_USERNAME = "00000000-0000-0000-0000-000000000000"
_MIN_REFRESH_TOKEN_LENGTH = 32


class UrlResponse(Protocol):
    def __enter__(self) -> UrlResponse: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def read(self) -> bytes: ...


UrlOpen = Callable[..., UrlResponse]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
_DEFAULT_URL_OPEN: UrlOpen = cast(UrlOpen, urllib.request.urlopen)
_DEFAULT_COMMAND_RUNNER: CommandRunner = cast(CommandRunner, subprocess.run)


def _decode_jwt_payload(token: str) -> Mapping[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise RuntimeError("ACR-scoped Entra token is not a JWT")
    encoded = parts[1]
    encoded += "=" * (-len(encoded) % 4)
    try:
        decoded = json.loads(base64.urlsafe_b64decode(encoded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("ACR-scoped Entra token payload is not decodable") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("ACR-scoped Entra token payload is not an object")
    return decoded


def _expected_writer_role(role_assignment_mode: str) -> str:
    mode = role_assignment_mode.strip()
    if mode in {"LegacyRegistryPermissions", "rbac"}:
        return "AcrPush"
    if mode in {"AbacRepositoryPermissions", "rbac-abac"}:
        return "Container Registry Repository Writer"
    raise RuntimeError(
        "Unsupported ACR role-assignment mode for publisher capability verification: "
        f"{mode}"
    )


def validate_authenticated_publisher_token(
    *,
    aad_access_token: str,
    tenant_id: str,
    role_assignment_mode: str,
) -> dict[str, object]:
    """Validate the short-lived publisher token without requiring RBAC-read privilege.

    Exact role-assignment topology is a control-plane bootstrap responsibility. The
    protected publisher intentionally does not receive Microsoft.Authorization role
    assignment read access merely to introspect its own permissions. Effective ACR
    capability is proven by OAuth exchange, Docker authentication, and the subsequent
    immutable registry push performed by the publication workflow.
    """
    token = aad_access_token.strip()
    tenant = tenant_id.strip()
    if not token:
        raise ValueError("aad_access_token is required")
    if not tenant:
        raise ValueError("tenant_id is required")

    payload = _decode_jwt_payload(token)
    principal_object_id = str(payload.get("oid") or "").strip()
    token_tenant_id = str(payload.get("tid") or "").strip()
    if not principal_object_id or not token_tenant_id:
        raise RuntimeError("ACR-scoped Entra token is missing oid/tid identity claims")
    if token_tenant_id.lower() != tenant.lower():
        raise RuntimeError("ACR-scoped Entra token tenant does not match Azure context")

    return {
        "schema_version": "ets.m365.gate2.publisher_capability_boundary.v1",
        "role_assignment_mode": role_assignment_mode.strip(),
        "expected_writer_role": _expected_writer_role(role_assignment_mode),
        "token_identity_claims_verified": True,
        "token_tenant_verified": True,
        "control_plane_rbac_verification": "bootstrap_operator_boundary",
        "runtime_rbac_enumeration_performed": False,
        "acr_oauth_exchange_verified": False,
        "docker_login_verified": False,
        "effective_push_verified": False,
        "customer_identifiers_retained": False,
        "reusable_credential_retained": False,
    }


def _oauth_error_code(body: bytes) -> str:
    try:
        decoded = json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return "unknown"
    candidates: list[object] = []
    if isinstance(decoded, dict):
        errors = decoded.get("errors")
        if isinstance(errors, list):
            for item in errors:
                if isinstance(item, dict):
                    candidates.append(item.get("code"))
        candidates.extend((decoded.get("code"), decoded.get("error")))
    for candidate in candidates:
        if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", candidate):
            return candidate
    return "unknown"


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
    try:
        with urlopen(request, timeout=30) as response:
            decoded = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        error_code = _oauth_error_code(exc.read())
        raise RuntimeError(
            "ACR OAuth exchange rejected the authenticated token "
            f"(HTTP {exc.code}, code={error_code})"
        ) from None
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
    runner: CommandRunner = _DEFAULT_COMMAND_RUNNER,
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
    role_assignment_mode = os.environ.get("ROLE_ASSIGNMENT_MODE", "")

    evidence = validate_authenticated_publisher_token(
        aad_access_token=access_token,
        tenant_id=tenant,
        role_assignment_mode=role_assignment_mode,
    )
    refresh_token = exchange_refresh_token(
        registry_server=server,
        tenant_id=tenant,
        aad_access_token=access_token,
    )
    evidence["acr_oauth_exchange_verified"] = True
    docker_login(registry_server=server, refresh_token=refresh_token)
    evidence["docker_login_verified"] = True

    evidence_dir = Path(os.environ.get("EVIDENCE_DIR", "evidence/host-az-q0-image"))
    evidence_path = evidence_dir / "authenticated-publisher-capability.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "Authenticated ACR publisher capability boundary verified: "
        "token tenant, OAuth exchange, and Docker login passed; exact RBAC topology "
        "remains bootstrap-controlled and effective push is proven by the subsequent "
        "immutable image publication."
    )


if __name__ == "__main__":
    authenticate_from_environment()
