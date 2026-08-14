"""Provider dispatch for connector credential references."""

from __future__ import annotations

from datetime import datetime

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialOperationUnsupportedError,
    CredentialProvider,
    CredentialProviderNotFoundError,
    MutableCredentialProvider,
)


class CredentialBroker:
    """Deterministic provider registry and credential-reference dispatcher."""

    def __init__(self) -> None:
        self._providers: dict[str, CredentialProvider] = {}

    def register(self, provider: CredentialProvider) -> None:
        scheme = provider.scheme.casefold()
        if scheme in self._providers:
            raise ValueError(f"duplicate credential provider scheme: {scheme}")
        self._providers[scheme] = provider

    def provider_for(self, reference: CredentialReferenceV1) -> CredentialProvider:
        try:
            return self._providers[reference.provider_scheme]
        except KeyError as exc:
            raise CredentialProviderNotFoundError(
                f"no credential provider registered for scheme {reference.provider_scheme!r}"
            ) from exc

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return self.provider_for(reference).describe(reference)

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        return self.provider_for(reference).resolve(reference)

    def create(
        self,
        reference: CredentialReferenceV1,
        material: bytes,
        *,
        expires_at_utc: datetime | None = None,
    ) -> CredentialMetadataV1:
        provider = self.provider_for(reference)
        if not isinstance(provider, MutableCredentialProvider):
            raise CredentialOperationUnsupportedError("credential provider is read-only")
        return provider.create(reference, material, expires_at_utc=expires_at_utc)

    def rotate(
        self,
        reference: CredentialReferenceV1,
        material: bytes,
        *,
        expires_at_utc: datetime | None = None,
    ) -> CredentialMetadataV1:
        provider = self.provider_for(reference)
        if not isinstance(provider, MutableCredentialProvider):
            raise CredentialOperationUnsupportedError("credential provider is read-only")
        return provider.rotate(reference, material, expires_at_utc=expires_at_utc)

    def revoke(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        provider = self.provider_for(reference)
        if not isinstance(provider, MutableCredentialProvider):
            raise CredentialOperationUnsupportedError("credential provider is read-only")
        return provider.revoke(reference)
