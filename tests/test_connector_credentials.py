from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.connectors.credentials import (
    CREDENTIAL_REFERENCE_SCHEMA_VERSION,
    CredentialAuditEventV1,
    CredentialBroker,
    CredentialProviderNotFoundError,
    CredentialReferenceV1,
    CredentialResolutionError,
    LocalCredentialRecord,
    LocalSealedCredentialProvider,
)

NOW = datetime(2026, 8, 13, 23, 30, tzinfo=UTC)


class MemoryBackend:
    def __init__(self) -> None:
        self.values: dict[str, LocalCredentialRecord] = {}

    def read(self, key: str) -> LocalCredentialRecord | None:
        return self.values.get(key)

    def write(self, key: str, record: LocalCredentialRecord) -> None:
        self.values[key] = record


class TestCodec:
    prefix = b"test-sealed:"

    def seal(self, material: bytes, *, context: str) -> bytes:
        return self.prefix + context.encode() + b":" + material

    def unseal(self, sealed_material: bytes, *, context: str) -> bytes:
        prefix = self.prefix + context.encode() + b":"
        if not sealed_material.startswith(prefix):
            raise ValueError("fixture context mismatch")
        return sealed_material[len(prefix) :]


def reference(value: str = "ets-local://connectors/demo") -> CredentialReferenceV1:
    return CredentialReferenceV1.model_validate(
        {"schema_version": CREDENTIAL_REFERENCE_SCHEMA_VERSION, "ref": value}
    )


def provider(
    *, audit: list[CredentialAuditEventV1] | None = None
) -> tuple[LocalSealedCredentialProvider, MemoryBackend]:
    backend = MemoryBackend()
    instance = LocalSealedCredentialProvider(
        backend,
        TestCodec(),
        audit_sink=None if audit is None else audit.append,
        clock=lambda: NOW,
    )
    return instance, backend


@pytest.mark.parametrize(
    "value",
    [
        "ets-local://user:pass@connectors/demo",
        "ets-local://connectors/demo?value=x",
        "ets-local://connectors/demo#fragment",
        "noscheme",
    ],
)
def test_reference_rejects_data_bearing_or_invalid_forms(value: str) -> None:
    with pytest.raises(ValidationError):
        reference(value)


def test_create_describe_and_management_serialization_are_material_free() -> None:
    instance, _ = provider()
    metadata = instance.create(reference(), b"runtime-value")

    assert metadata.status == "available"
    assert metadata.version == "1"
    serialized = metadata.model_dump_json()
    assert "runtime-value" not in serialized
    assert "sealed" not in serialized


def test_resolve_returns_redacted_zeroizable_lease() -> None:
    instance, _ = provider()
    instance.create(reference(), b"runtime-value")

    lease = instance.resolve(reference())
    assert lease.reveal() == b"runtime-value"
    assert "runtime-value" not in repr(lease)
    lease.close()
    with pytest.raises(Exception, match="closed"):
        lease.reveal()


def test_rotation_changes_provider_version_without_changing_reference() -> None:
    instance, _ = provider()
    original = instance.create(reference(), b"v1")
    rotated = instance.rotate(reference(), b"v2")

    assert original.reference == rotated.reference
    assert original.version == "1"
    assert rotated.version == "2"
    with instance.resolve(reference()) as lease:
        assert lease.reveal() == b"v2"


def test_revoked_reference_fails_closed() -> None:
    instance, _ = provider()
    instance.create(reference(), b"value")
    metadata = instance.revoke(reference())

    assert metadata.status == "revoked"
    with pytest.raises(CredentialResolutionError) as exc_info:
        instance.resolve(reference())
    assert exc_info.value.status == "revoked"


def test_expired_reference_fails_closed() -> None:
    instance, backend = provider()
    instance.create(reference(), b"value")
    record = backend.values["connectors/demo"]
    backend.values["connectors/demo"] = replace(
        record,
        expires_at_utc=NOW - timedelta(seconds=1),
    )

    assert instance.describe(reference()).status == "expired"
    with pytest.raises(CredentialResolutionError) as exc_info:
        instance.resolve(reference())
    assert exc_info.value.status == "expired"


def test_missing_reference_fails_closed() -> None:
    instance, _ = provider()

    assert instance.describe(reference()).status == "missing"
    with pytest.raises(CredentialResolutionError) as exc_info:
        instance.resolve(reference())
    assert exc_info.value.status == "missing"


def test_audit_events_are_redacted_and_versioned() -> None:
    audit: list[CredentialAuditEventV1] = []
    instance, _ = provider(audit=audit)
    instance.create(reference(), b"value-one")
    instance.rotate(reference(), b"value-two")
    instance.revoke(reference())

    assert [event.event_type for event in audit] == [
        "credential.created",
        "credential.rotated",
        "credential.revoked",
    ]
    serialized = "\n".join(event.model_dump_json() for event in audit)
    assert "value-one" not in serialized
    assert "value-two" not in serialized
    assert "ets-local://connectors/demo" not in serialized


def test_broker_dispatches_by_reference_scheme() -> None:
    instance, _ = provider()
    broker = CredentialBroker()
    broker.register(instance)
    broker.create(reference(), b"value")

    assert broker.describe(reference()).status == "available"
    with broker.resolve(reference()) as lease:
        assert lease.reveal() == b"value"


def test_broker_rejects_unknown_provider_scheme() -> None:
    broker = CredentialBroker()
    with pytest.raises(CredentialProviderNotFoundError):
        broker.describe(reference("external-vault://team/demo"))
