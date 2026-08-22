"""Read-only Microsoft Graph credential provider backed by Azure managed identity."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit

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
MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE = "azure-mi://microsoft-graph/directory"
MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE = "azure-mi://office-365-management/purview"
MICROSOFT_GRAPH_DEFAULT_SCOPE = "https://graph.microsoft.com/.default"
MICROSOFT_PURVIEW_DEFAULT_SCOPE = "https://manage.office.com/.default"


class ManagedIdentityAccessToken(Protocol):
    """Minimum access-token shape required from azure-identity."""

    token: str
    expires_on: int


class ManagedIdentityTokenCredential(Protocol):
    """Minimum managed-identity credential behavior used by the connector broker."""

    def get_token(self, *scopes: str) -> ManagedIdentityAccessToken: ...

    def close(self) -> None: ...


Clock = Callable[[], datetime]
CredentialFactory = Callable[[str], ManagedIdentityTokenCredential]


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


@dataclass(frozen=True, slots=True)
class AzureManagedIdentityCredentialProfile:
    """Server-owned mapping from one opaque reference to one UAMI and token audience."""

    reference: str
    client_id: str
    scope: str

    def __post_init__(self) -> None:
        reference = self.reference.strip()
        parsed_reference = parse_credential_reference(reference)
        if parsed_reference.scheme != AZURE_MANAGED_IDENTITY_SCHEME:
            raise ValueError("managed identity profile requires the azure-mi scheme")

        client_id = self.client_id.strip()
        if not client_id:
            raise ValueError("managed identity profile client_id is required")
        if len(client_id) > 100:
            raise ValueError("managed identity profile client_id exceeds configured bound")

        scope = self.scope.strip()
        parsed_scope = urlsplit(scope)
        if (
            parsed_scope.scheme != "https"
            or not parsed_scope.hostname
            or parsed_scope.port not in {None, 443}
            or parsed_scope.username is not None
            or parsed_scope.password is not None
            or parsed_scope.query
            or parsed_scope.fragment
            or parsed_scope.path != "/.default"
        ):
            raise ValueError(
                "managed identity profile scope must be an HTTPS resource .default audience"
            )

        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "client_id", client_id)
        object.__setattr__(self, "scope", scope)


class AzureManagedIdentityCredentialProvider:
    """Route approved credential references to distinct UAMIs and token audiences."""

    scheme = AZURE_MANAGED_IDENTITY_SCHEME

    def __init__(
        self,
        profiles: tuple[AzureManagedIdentityCredentialProfile, ...],
        *,
        credentials: dict[str, ManagedIdentityTokenCredential] | None = None,
        credential_factory: CredentialFactory = _load_managed_identity_credential,
        clock: Clock = _utc_now,
    ) -> None:
        if not profiles:
            raise ValueError("at least one managed identity profile is required")
        by_reference: dict[str, AzureManagedIdentityCredentialProfile] = {}
        for profile in profiles:
            key = profile.reference.casefold()
            if key in by_reference:
                raise ValueError("managed identity profile references must be unique")
            by_reference[key] = profile
        supplied = dict(credentials or {})
        configured_client_ids = {profile.client_id for profile in profiles}
        if set(supplied) - configured_client_ids:
            raise ValueError("managed identity credentials include an unconfigured client_id")
        self._profiles = by_reference
        self._credentials = supplied
        self._credential_factory = credential_factory
        self._clock = clock

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        """Describe a configured identity route without acquiring a token."""

        self._profile(reference)
        now = self._now()
        return self._metadata(reference, version=None, expires_at_utc=None, updated_at_utc=now)

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        """Acquire a short-lived token only from the reference's designated UAMI/audience."""

        profile = self._profile(reference)
        now = self._now()
        credential = self._credentials.get(profile.client_id)
        if credential is None:
            try:
                credential = self._credential_factory(profile.client_id)
            except Exception as exc:
                raise CredentialResolutionError(
                    "unavailable",
                    "Azure managed identity credential initialization failed",
                ) from exc
            self._credentials[profile.client_id] = credential
        try:
            access_token = credential.get_token(profile.scope)
        except Exception as exc:
            raise CredentialResolutionError(
                "unavailable",
                "Azure managed identity could not acquire the configured audience token",
            ) from exc

        material, expires_on, expires_at_utc = _validated_access_token(access_token, now=now)
        metadata = self._metadata(
            reference,
            version=str(expires_on),
            expires_at_utc=expires_at_utc,
            updated_at_utc=now,
        )
        return CredentialLease(material, metadata)

    def close(self) -> None:
        """Release every initialized managed-identity transport exactly once."""

        closed: set[int] = set()
        for credential in self._credentials.values():
            identity = id(credential)
            if identity in closed:
                continue
            credential.close()
            closed.add(identity)

    def _profile(
        self,
        reference: CredentialReferenceV1,
    ) -> AzureManagedIdentityCredentialProfile:
        parsed = parse_credential_reference(reference.ref)
        if parsed.scheme != self.scheme:
            raise CredentialProviderError(
                f"credential reference scheme {parsed.scheme!r} does not match provider"
            )
        profile = self._profiles.get(reference.ref.casefold())
        if profile is None:
            raise CredentialProviderError(
                "Azure managed-identity provider rejected an unconfigured reference"
            )
        return profile

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


class AzureManagedIdentityGraphCredentialProvider(AzureManagedIdentityCredentialProvider):
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
        profile = AzureManagedIdentityCredentialProfile(
            reference=MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
            client_id=normalized_client_id,
            scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
        )
        super().__init__(
            (profile,),
            credentials=(
                {normalized_client_id: credential}
                if credential is not None
                else None
            ),
            clock=clock,
        )


def _validated_access_token(
    access_token: ManagedIdentityAccessToken,
    *,
    now: datetime,
) -> tuple[bytes, int, datetime]:
    token = access_token.token
    if not token:
        raise CredentialResolutionError(
            "unavailable",
            "Azure managed identity returned an empty token",
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
            "Azure managed identity returned an expired token",
        )
    return material, expires_on, expires_at_utc
