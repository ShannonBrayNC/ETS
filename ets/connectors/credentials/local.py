"""Local sealed credential provider for ETS Gateway pilot deployments."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol

from ets.connectors.credentials.models import (
    CREDENTIAL_AUDIT_SCHEMA_VERSION,
    CREDENTIAL_METADATA_SCHEMA_VERSION,
    CredentialAuditEventV1,
    CredentialMetadataV1,
    CredentialReferenceV1,
    credential_reference_fingerprint,
    parse_credential_reference,
)
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialProviderError,
    CredentialResolutionError,
)


@dataclass(frozen=True, slots=True)
class LocalCredentialRecord:
    """Opaque sealed record persisted by the local host backend."""

    sealed_material: bytes
    version: int
    revoked: bool
    expires_at_utc: datetime | None
    updated_at_utc: datetime


class SealedCredentialBackend(Protocol):
    """Persistence boundary implemented by the appliance host."""

    def read(self, key: str) -> LocalCredentialRecord | None: ...

    def write(self, key: str, record: LocalCredentialRecord) -> None: ...


class CredentialSealCodec(Protocol):
    """Host sealing boundary; production pilots should bind this to hardware-backed sealing."""

    def seal(self, material: bytes, *, context: str) -> bytes: ...

    def unseal(self, sealed_material: bytes, *, context: str) -> bytes: ...


AuditSink = Callable[[CredentialAuditEventV1], None]
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class LocalSealedCredentialProvider:
    """Mutable local provider that delegates persistence and sealing to host boundaries."""

    scheme = "ets-local"

    def __init__(
        self,
        backend: SealedCredentialBackend,
        codec: CredentialSealCodec,
        *,
        audit_sink: AuditSink | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        self._backend = backend
        self._codec = codec
        self._audit_sink = audit_sink
        self._clock = clock

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        key = self._key(reference)
        record = self._backend.read(key)
        now = self._now()
        if record is None:
            return self._metadata(reference, "missing", None, None, now)
        status = "revoked" if record.revoked else "available"
        if not record.revoked and record.expires_at_utc is not None:
            if record.expires_at_utc <= now:
                status = "expired"
        return self._metadata(
            reference,
            status,
            str(record.version),
            record.expires_at_utc,
            record.updated_at_utc,
        )

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        key = self._key(reference)
        metadata = self.describe(reference)
        if metadata.status != "available":
            self._audit(
                "credential.resolve_failed",
                reference,
                metadata.version,
                "failure",
                metadata.status,
            )
            raise CredentialResolutionError(
                metadata.status,
                f"credential is not available: {metadata.status}",
            )
        record = self._backend.read(key)
        if record is None:
            raise CredentialResolutionError("missing", "credential is not available: missing")
        try:
            material = self._codec.unseal(record.sealed_material, context=key)
        except Exception as exc:
            self._audit(
                "credential.resolve_failed",
                reference,
                metadata.version,
                "failure",
                "unavailable",
            )
            raise CredentialResolutionError(
                "unavailable", "credential provider could not resolve material"
            ) from exc
        return CredentialLease(material, metadata)

    def create(
        self,
        reference: CredentialReferenceV1,
        material: bytes,
        *,
        expires_at_utc: datetime | None = None,
    ) -> CredentialMetadataV1:
        key = self._key(reference)
        if self._backend.read(key) is not None:
            raise CredentialProviderError("credential reference already exists")
        now = self._now()
        expiry = self._normalize_expiry(expires_at_utc)
        sealed = self._codec.seal(self._require_material(material), context=key)
        record = LocalCredentialRecord(sealed, 1, False, expiry, now)
        self._backend.write(key, record)
        metadata = self._metadata(reference, "available", "1", expiry, now)
        self._audit("credential.created", reference, "1", "success", "available")
        return metadata

    def rotate(
        self,
        reference: CredentialReferenceV1,
        material: bytes,
        *,
        expires_at_utc: datetime | None = None,
    ) -> CredentialMetadataV1:
        key = self._key(reference)
        existing = self._backend.read(key)
        if existing is None:
            raise CredentialResolutionError("missing", "credential cannot be rotated: missing")
        now = self._now()
        expiry = self._normalize_expiry(expires_at_utc)
        version = existing.version + 1
        sealed = self._codec.seal(self._require_material(material), context=key)
        record = LocalCredentialRecord(sealed, version, False, expiry, now)
        self._backend.write(key, record)
        metadata = self._metadata(reference, "available", str(version), expiry, now)
        self._audit(
            "credential.rotated",
            reference,
            str(version),
            "success",
            "available",
        )
        return metadata

    def revoke(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        key = self._key(reference)
        existing = self._backend.read(key)
        if existing is None:
            raise CredentialResolutionError("missing", "credential cannot be revoked: missing")
        now = self._now()
        updated = replace(existing, revoked=True, updated_at_utc=now)
        self._backend.write(key, updated)
        metadata = self._metadata(
            reference,
            "revoked",
            str(updated.version),
            updated.expires_at_utc,
            now,
        )
        self._audit(
            "credential.revoked",
            reference,
            str(updated.version),
            "success",
            "revoked",
        )
        return metadata

    def _key(self, reference: CredentialReferenceV1) -> str:
        parsed = parse_credential_reference(reference.ref)
        if parsed.scheme != self.scheme:
            raise CredentialProviderError(
                f"credential reference scheme {parsed.scheme!r} does not match provider"
            )
        identifier = f"{parsed.netloc}{parsed.path}".strip("/")
        if not identifier:
            raise CredentialProviderError("local credential reference has no identifier")
        return identifier

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise CredentialProviderError("credential provider clock must be timezone-aware")
        return value.astimezone(UTC)

    @staticmethod
    def _normalize_expiry(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("credential expiry must be timezone-aware")
        return value.astimezone(UTC)

    @staticmethod
    def _require_material(material: bytes) -> bytes:
        if not material:
            raise ValueError("credential material must not be empty")
        return material

    @staticmethod
    def _metadata(
        reference: CredentialReferenceV1,
        status: str,
        version: str | None,
        expires_at_utc: datetime | None,
        updated_at_utc: datetime,
    ) -> CredentialMetadataV1:
        return CredentialMetadataV1.model_validate(
            {
                "schema_version": CREDENTIAL_METADATA_SCHEMA_VERSION,
                "reference": reference.model_dump(mode="python"),
                "provider": "ets-local",
                "status": status,
                "version": version,
                "expires_at_utc": expires_at_utc,
                "updated_at_utc": updated_at_utc,
            }
        )

    def _audit(
        self,
        event_type: str,
        reference: CredentialReferenceV1,
        version: str | None,
        outcome: str,
        status: str,
    ) -> None:
        if self._audit_sink is None:
            return
        event = CredentialAuditEventV1.model_validate(
            {
                "schema_version": CREDENTIAL_AUDIT_SCHEMA_VERSION,
                "event_type": event_type,
                "provider": self.scheme,
                "reference_fingerprint": credential_reference_fingerprint(reference),
                "version": version,
                "outcome": outcome,
                "status": status,
                "occurred_at_utc": self._now(),
            }
        )
        self._audit_sink(event)
