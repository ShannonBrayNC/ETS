"""Managed-identity bearer provider for the private ETS Core relay boundary."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from typing import Protocol

from ets.connectors.credentials.models import (
    CREDENTIAL_METADATA_SCHEMA_VERSION,
    CREDENTIAL_REFERENCE_SCHEMA_VERSION,
    CredentialMetadataV1,
    CredentialReferenceV1,
)
from ets.connectors.credentials.provider import CredentialLease
from ets.gateway.core_relay import CoreRelayTerminalError, ScopedBearerLease


class ManagedIdentityAccessToken(Protocol):
    token: str
    expires_on: int


class ManagedIdentityTokenCredential(Protocol):
    def get_token(self, *scopes: str) -> ManagedIdentityAccessToken: ...

    def close(self) -> None: ...


def _load_managed_identity_credential(client_id: str) -> ManagedIdentityTokenCredential:
    try:
        module = importlib.import_module("azure.identity")
    except ModuleNotFoundError as exc:
        raise CoreRelayTerminalError(
            "azure-identity is required for hosted Gateway Core relay"
        ) from exc
    factory = getattr(module, "ManagedIdentityCredential", None)
    if factory is None:
        raise CoreRelayTerminalError(
            "azure.identity.ManagedIdentityCredential is unavailable"
        )
    credential: ManagedIdentityTokenCredential = factory(client_id=client_id)
    return credential


class AzureManagedIdentityCoreTokenProvider:
    """Acquire one fixed-scope ETS API token for one fixed tenant/workspace mapping."""

    def __init__(
        self,
        *,
        client_id: str,
        core_scope: str,
        tenant_id: str,
        workspace_id: str,
        credential: ManagedIdentityTokenCredential | None = None,
    ) -> None:
        self._client_id = _required_bounded(client_id, "client_id", maximum=100)
        self._core_scope = _validate_scope(core_scope)
        self._tenant_id = _required_bounded(tenant_id, "tenant_id", maximum=200)
        self._workspace_id = _required_bounded(workspace_id, "workspace_id", maximum=200)
        self._credential = credential or _load_managed_identity_credential(self._client_id)
        self._reference = CredentialReferenceV1.model_validate(
            {
                "schema_version": CREDENTIAL_REFERENCE_SCHEMA_VERSION,
                "ref": "azure-mi://ets-core-relay",
            }
        )

    def acquire(self, *, tenant_id: str, workspace_id: str) -> ScopedBearerLease:
        """Acquire a short-lived token only for the configured server-authoritative scope."""

        if tenant_id != self._tenant_id or workspace_id != self._workspace_id:
            raise CoreRelayTerminalError(
                "Gateway relay requested a tenant/workspace outside its configured ETS scope"
            )
        try:
            access_token = self._credential.get_token(self._core_scope)
        except Exception as exc:
            raise CoreRelayTerminalError(
                "Gateway managed identity could not acquire an ETS Core token"
            ) from exc

        token = access_token.token
        if not token:
            raise CoreRelayTerminalError(
                "Gateway managed identity returned an empty ETS Core token"
            )
        try:
            material = token.encode("ascii")
        except UnicodeEncodeError as exc:
            raise CoreRelayTerminalError(
                "Gateway managed identity returned non-ASCII ETS Core token material"
            ) from exc

        try:
            expires_on = int(access_token.expires_on)
            expires_at_utc = datetime.fromtimestamp(expires_on, tz=UTC)
        except (OverflowError, OSError, TypeError, ValueError) as exc:
            raise CoreRelayTerminalError(
                "Gateway managed identity returned an invalid ETS Core token expiry"
            ) from exc
        now = datetime.now(UTC)
        if expires_at_utc <= now:
            raise CoreRelayTerminalError(
                "Gateway managed identity returned an expired ETS Core token"
            )

        metadata = CredentialMetadataV1.model_validate(
            {
                "schema_version": CREDENTIAL_METADATA_SCHEMA_VERSION,
                "reference": self._reference.model_dump(mode="python"),
                "provider": "azure-managed-identity",
                "status": "available",
                "version": str(expires_on),
                "expires_at_utc": expires_at_utc,
                "updated_at_utc": now,
            }
        )
        return CredentialLease(material, metadata)

    def close(self) -> None:
        """Release the Azure Identity transport session."""

        self._credential.close()


def _required_bounded(value: str, name: str, *, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{name} exceeds configured bound")
    return normalized


def _validate_scope(value: str) -> str:
    scope = _required_bounded(value, "core_scope", maximum=500)
    if not scope.endswith("/.default"):
        raise ValueError("core_scope must be a fixed resource .default scope")
    if any(character.isspace() for character in scope):
        raise ValueError("core_scope must not contain whitespace")
    if not (scope.startswith("api://") or scope.startswith("https://")):
        raise ValueError("core_scope must use an api:// or https:// resource identifier")
    return scope
