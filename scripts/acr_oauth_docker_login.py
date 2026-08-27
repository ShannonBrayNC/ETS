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
_ACR_PUSH_ROLE_ID = "8311e382-0749-4cb8-b61a-304f252e45ec"


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


def _run_text(
    args: list[str],
    *,
    runner: CommandRunner,
) -> str:
    completed = runner(
        args,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _role_definition_leaf(assignment: Mapping[str, Any]) -> str:
    definition = str(assignment.get("roleDefinitionId") or "").rstrip("/")
    return definition.rsplit("/", 1)[-1] if definition else ""


def verify_authenticated_publisher_rbac(
    *,
    registry_server: str,
    aad_access_token: str,
    role_assignment_mode: str,
    runner: CommandRunner = _DEFAULT_COMMAND_RUNNER,
) -> dict[str, object]:
    """Verify the actual OIDC-authenticated principal owns the direct ACR writer role."""
    server = registry_server.strip()
    token = aad_access_token.strip()
    mode = role_assignment_mode.strip()
    if not server or "/" in server or "://" in server:
        raise ValueError("registry_server must be an ACR login hostname")
    if not token:
        raise ValueError("aad_access_token is required")
    if not server.endswith(".azurecr.io") or not server.removesuffix(".azurecr.io"):
        raise RuntimeError(
            "Q0 publisher RBAC verification requires an Azure public-cloud "
            "ACR login server"
        )

    payload = _decode_jwt_payload(token)
    principal_object_id = str(payload.get("oid") or "").strip()
    tenant_id = str(payload.get("tid") or "").strip()
    if not principal_object_id or not tenant_id:
        raise RuntimeError("ACR-scoped Entra token is missing oid/tid identity claims")

    registry_name = server.removesuffix(".azurecr.io")
    registry_id = _run_text(
        ["az", "acr", "show", "--name", registry_name, "--query", "id", "-o", "tsv"],
        runner=runner,
    )
    if not registry_id.startswith("/subscriptions/"):
        raise RuntimeError(
            "Unable to resolve the approved ACR resource id for publisher verification"
        )

    assignments_json = _run_text(
        [
            "az",
            "role",
            "assignment",
            "list",
            "--scope",
            registry_id,
            "--assignee-object-id",
            principal_object_id,
            "--fill-principal-name",
            "false",
            "--output",
            "json",
        ],
        runner=runner,
    )
    decoded_assignments = json.loads(assignments_json or "[]")
    if not isinstance(decoded_assignments, list):
        raise RuntimeError("Azure role-assignment query returned a non-list payload")
    assignments = [item for item in decoded_assignments if isinstance(item, dict)]
    direct = [
        item
        for item in assignments
        if str(item.get("scope") or "").lower() == registry_id.lower()
        and str(item.get("principalType") or "").lower() == "serviceprincipal"
    ]

    expected_role = ""
    matching: list[Mapping[str, Any]] = []
    if mode in {"LegacyRegistryPermissions", "rbac"}:
        expected_role = "AcrPush"
        matching = [
            item
            for item in direct
            if _role_definition_leaf(item).lower() == _ACR_PUSH_ROLE_ID.lower()
            or str(item.get("roleDefinitionName") or "").lower() == "acrpush"
        ]
    elif mode in {"AbacRepositoryPermissions", "rbac-abac"}:
        expected_role = "Container Registry Repository Writer"
        matching = [
            item
            for item in direct
            if str(item.get("roleDefinitionName") or "").lower()
            == "container registry repository writer"
        ]
    else:
        raise RuntimeError(
            "Unsupported ACR role-assignment mode for Q0 publisher verification: "
            f"{mode}"
        )

    if len(matching) != 1:
        raise RuntimeError(
            "Authenticated GitHub OIDC principal does not have exactly one direct "
            f"{expected_role} assignment at the approved ACR scope"
        )

    return {
        "schema_version": "ets.host_az.q0_authenticated_publisher_rbac.v1",
        "role_assignment_mode": mode,
        "expected_writer_role": expected_role,
        "authenticated_service_principal": True,
        "direct_registry_scope_verified": True,
        "authenticated_writer_role_verified": True,
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
    rbac_evidence = verify_authenticated_publisher_rbac(
        registry_server=server,
        aad_access_token=access_token,
        role_assignment_mode=role_assignment_mode,
    )
    evidence_path = Path("evidence/host-az-q0-image/authenticated-publisher-rbac.json")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(rbac_evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "Authenticated Q0 publisher RBAC boundary verified: "
        f"{rbac_evidence['expected_writer_role']} at approved ACR scope."
    )
    refresh_token = exchange_refresh_token(
        registry_server=server,
        tenant_id=tenant,
        aad_access_token=access_token,
    )
    docker_login(registry_server=server, refresh_token=refresh_token)


if __name__ == "__main__":
    authenticate_from_environment()
