"""Read-only Microsoft Graph credential provider backed by Azure managed identity."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from ets.connectors.credentials.models import (
    CREDENTIAL_METADATA_SCHEMA_VERSION,
    CredentialMetadataV1,
    CredentialReferenceV1,
    parse_credential_reference,
)
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialProviderError,
    CredentialResolutionError,
)

AZURE_MANAGED_IDENTITY_SCHEME = "azure-mi"
MICROSOFT_GRAPH_CREDENTIAL_REFERENCE = "azure-mi://microsoft-graph"
MICROSOFT_GRAPH_DEFAULT_SCOPE = "https://graph.microsoft.com/.default"


class ManagedIdentityAccessToken(Protocol):
    """Minimum access-token shape required from azure-identity."""

    token: str
    expires_on: int


class ManagedIdentityTokenCredential(Protocol):
    """Minimum managed-identity credential behavior used by the connector broker."""

    def get_token(self, *scopes: str) -> ManagedIdentityAccessToken: ...

    def close(self) -> None: ...


Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_managed_identity_credential(client_id: str) -> ManagedIdentityTokenCredential:
    try:
        module = importlib.import_module("azure.identity")
    except ModuleNotFoundError as exc:
        raise CredentialProviderError(
            "azure-identity is required for the Azure managed-identity credential provider"
        ) from exc

    factory = getattr(module, "ManagedIdentityCredential", None)
    if factory is None:
        raise CredentialProviderError(
            "azure.identity.ManagedIdentityCredential is unavailable"
        )
    credential: ManagedIdentityTokenCredential = factory(client_id=client_id)
    return credential


class AzureManagedIdentityGraphCredentialProvider:
    """Acquire short-lived Microsoft Graph tokens using one user-assigned managed identity."""

    scheme = AZURE_MANAGED_IDENTITY_SCHEME

    def __init__(
        self,
        *,
        client_id: str,
        credential: ManagedIdentityTokenCredential | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        normalized_client_id = client_id.strip()
        if not normalized_client_id:
            raise ValueError("managed identity client_id is required")
        if len(normalized_client_id) > 100:
            raise ValueError("managed identity client_id exceeds configured bound")
        self._client_id = normalized_client_id
        self._credential = credential or _load_managed_identity_credential(normalized_client_id)
        self._clock = clock

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        """Describe the configured identity without acquiring reusable credential material."""

        self._validate_reference(reference)
        now = self._now()
        return self._metadata(reference, version=None, expires_at_utc=None, updated_at_utc=now)

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        """Acquire one short-lived Graph token and return it in a zeroizable runtime lease."""

        self._validate_reference(reference)
        now = self._now()
        try:
            access_token = self._credential.get_token(MICROSOFT_GRAPH_DEFAULT_SCOPE)
        except Exception as exc:
            raise CredentialResolutionError(
                "unavailable",
                "Azure managed identity could not acquire a Microsoft Graph token",
            ) from exc

        token = access_token.token
        if not token:
            raise CredentialResolutionError(
                "unavailable",
                "Azure managed identity returned an empty Microsoft Graph token",
            )
        try:
            material = token.encode("ascii")
        except UnicodeEncodeError as exc:
            raise CredentialResolutionError(
                "incompatible",
                "Azure managed identity returned non-ASCII token material",
            ) from exc

        try:
            expires_on = int(access_token.expires_on)
            expires_at_utc = datetime.fromtimestamp(expires_on, tz=UTC)
        except (OverflowError, OSError, TypeError, ValueError) as exc:
            raise CredentialResolutionError(
                "incompatible",
                "Azure managed identity returned an invalid token expiry",
            ) from exc
        if expires_at_utc <= now:
            raise CredentialResolutionError(
                "expired",
                "Azure managed identity returned an expired Microsoft Graph token",
            )

        metadata = self._metadata(
            reference,
            version=str(expires_on),
            expires_at_utc=expires_at_utc,
            updated_at_utc=now,
        )
        return CredentialLease(material, metadata)

    def close(self) -> None:
        """Release the underlying Azure Identity transport session."""

        self._credential.close()

    def _validate_reference(self, reference: CredentialReferenceV1) -> None:
        parsed = parse_credential_reference(reference.ref)
        if parsed.scheme != self.scheme:
            raise CredentialProviderError(
                f"credential reference scheme {parsed.scheme!r} does not match provider"
            )
        if reference.ref.casefold() != MICROSOFT_GRAPH_CREDENTIAL_REFERENCE.casefold():
            raise CredentialProviderError(
                "Azure managed-identity provider accepts only the Microsoft Graph credential"
            )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise CredentialProviderError("credential provider clock must be timezone-aware")
        return value.astimezone(UTC)

    @staticmethod
    def _metadata(
        reference: CredentialReferenceV1,
        *,
        version: str | None,
        expires_at_utc: datetime | None,
        updated_at_utc: datetime,
    ) -> CredentialMetadataV1:
        return CredentialMetadataV1.model_validate(
            {
                "schema_version": CREDENTIAL_METADATA_SCHEMA_VERSION,
                "reference": reference.model_dump(mode="python"),
                "provider": "azure-managed-identity",
                "status": "available",
                "version": version,
                "expires_at_utc": expires_at_utc,
                "updated_at_utc": updated_at_utc,
            }
        )
