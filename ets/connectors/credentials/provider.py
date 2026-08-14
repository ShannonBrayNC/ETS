"""Credential-provider contracts and runtime-only credential leases."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from ets.connectors.credentials.models import (
    CredentialMetadataV1,
    CredentialReferenceV1,
    CredentialStatus,
)


class CredentialProviderError(RuntimeError):
    """Base credential-provider error."""


class CredentialResolutionError(CredentialProviderError):
    """Raised when a credential reference cannot produce usable runtime material."""

    def __init__(self, status: CredentialStatus, message: str) -> None:
        super().__init__(message)
        self.status = status


class CredentialProviderNotFoundError(CredentialProviderError):
    """Raised when no provider is registered for a reference scheme."""


class CredentialOperationUnsupportedError(CredentialProviderError):
    """Raised when a provider does not implement a requested lifecycle operation."""


class CredentialLease:
    """Short-lived runtime credential bytes with redacted representation and zeroization."""

    __slots__ = ("_closed", "_material", "metadata")

    def __init__(self, material: bytes, metadata: CredentialMetadataV1) -> None:
        if not material:
            raise ValueError("credential material must not be empty")
        self._material = bytearray(material)
        self.metadata = metadata
        self._closed = False

    def __repr__(self) -> str:
        return (
            "CredentialLease(material=<redacted>, "
            f"provider={self.metadata.provider!r}, version={self.metadata.version!r})"
        )

    def reveal(self) -> bytes:
        if self._closed:
            raise CredentialProviderError("credential lease is closed")
        return bytes(self._material)

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._material)):
            self._material[index] = 0
        self._closed = True

    def __enter__(self) -> CredentialLease:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


@runtime_checkable
class CredentialProvider(Protocol):
    """Read/resolve contract implemented by local and enterprise providers."""

    @property
    def scheme(self) -> str: ...

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1: ...

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


@runtime_checkable
class MutableCredentialProvider(CredentialProvider, Protocol):
    """Optional lifecycle contract for providers that permit writes/rotation."""

    def create(
        self,
        reference: CredentialReferenceV1,
        material: bytes,
        *,
        expires_at_utc: datetime | None = None,
    ) -> CredentialMetadataV1: ...

    def rotate(
        self,
        reference: CredentialReferenceV1,
        material: bytes,
        *,
        expires_at_utc: datetime | None = None,
    ) -> CredentialMetadataV1: ...

    def revoke(self, reference: CredentialReferenceV1) -> CredentialMetadataV1: ...
