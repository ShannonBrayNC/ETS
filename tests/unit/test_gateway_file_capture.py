from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from ets.capture.filesystem_object import FilesystemObjectDigest, FilesystemObjectMetadata
from ets.capture.object_digest import StreamDigestResult
from ets.gateway.file_capture import (
    GatewayFileCaptureError,
    GatewayFileCaptureRequest,
    build_file_capture,
)
from ets.gateway.source_registry import SourceRegistration

PRINCIPAL = "spiffe://example.test/workload/file-drop"


def registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="file-drop-a",
        source_system="filesystem",
        tenant_id="tenant_authoritative",
        workspace_id="workspace_authoritative",
        adapter_id="gateway-file",
        adapter_version="1.0",
        event_type="file.observed",
        classification="internal",
        redaction_profile="file-metadata-v1",
        minimization_profile="file-digest-metadata-v1",
        clock_quality="synchronized",
    )


def observation(payload: bytes = b"file-payload", *, relative_path: str = "drop/a.bin") -> FilesystemObjectDigest:
    digest = StreamDigestResult(
        algorithm="sha256",
        value=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        declared_length=len(payload),
    )
    metadata = FilesystemObjectMetadata(
        device=7,
        inode=11,
        size=len(payload),
        mtime_ns=123456789,
        ctime_ns=123456700,
    )
    return FilesystemObjectDigest(
        relative_path=relative_path,
        digest=digest,
        observed_before=metadata,
        observed_after=metadata,
    )


def request(payload: bytes = b"file-payload", *, delivery_id: str = "delivery-1") -> GatewayFileCaptureRequest:
    return GatewayFileCaptureRequest(
        observation=observation(payload),
        delivery_id=delivery_id,
        declared_filename="source-name.bin",
        declared_content_type="application/octet-stream",
        correlation_id="corr-1",
        received_at_utc=datetime(2026, 8, 14, 1, 0, tzinfo=UTC),
    )


def test_file_capture_uses_authoritative_scope_and_declared_representation() -> None:
    mapped = build_file_capture(registration(), request())
    envelope = mapped.envelope

    assert envelope.source.tenant_id == "tenant_authoritative"
    assert envelope.source.workspace_id == "workspace_authoritative"
    assert envelope.source.transport_identity == PRINCIPAL
    assert envelope.source.idempotency_key == "file:delivery-1"
    assert envelope.content_digest.value == hashlib.sha256(mapped.committed_representation).hexdigest()
    assert envelope.metadata["object_digest"] == hashlib.sha256(b"file-payload").hexdigest()
    assert envelope.metadata["declared_filename_claim"] == "source-name.bin"
    assert envelope.metadata["relative_path"] == "drop/a.bin"
    assert envelope.privacy.contains_raw_evidence is False
    assert envelope.evidence_reference.retention_mode == "not_retained"


def test_file_capture_is_deterministic_for_same_observation() -> None:
    first = build_file_capture(registration(), request())
    second = build_file_capture(registration(), request())

    assert first.committed_representation == second.committed_representation
    assert first.envelope.content_digest == second.envelope.content_digest
    assert first.envelope.capture_id == second.envelope.capture_id


def test_file_capture_keeps_raw_marker_out_of_committed_surfaces() -> None:
    marker = b"RAW-FILE-SECRET-MARKER"
    mapped = build_file_capture(registration(), request(marker))

    assert marker not in mapped.committed_representation
    assert marker.decode() not in repr(mapped.envelope)


def test_file_capture_rejects_unstable_or_precommitted_observation() -> None:
    base = observation()
    with pytest.raises(GatewayFileCaptureError, match="not qualified as stable"):
        build_file_capture(registration(), replace(request(), observation=replace(base, stability="changed")))
    with pytest.raises(GatewayFileCaptureError, match="already carries commitment"):
        build_file_capture(
            registration(),
            replace(request(), observation=replace(base, commitment_state="committed")),
        )


def test_file_capture_rejects_raw_retention_and_digest_size_mismatch() -> None:
    base = observation()
    with pytest.raises(GatewayFileCaptureError, match="raw object retention"):
        build_file_capture(
            registration(),
            replace(request(), observation=replace(base, raw_object_retained=True)),
        )
    bad_digest = replace(base.digest, byte_count=base.digest.byte_count + 1)
    with pytest.raises(GatewayFileCaptureError, match="byte count"):
        build_file_capture(
            registration(),
            replace(request(), observation=replace(base, digest=bad_digest)),
        )


def test_file_capture_enforces_delivery_claim_and_representation_bounds() -> None:
    with pytest.raises(GatewayFileCaptureError, match="delivery_id"):
        build_file_capture(registration(), replace(request(), delivery_id=""))
    with pytest.raises(GatewayFileCaptureError, match="declared_filename"):
        build_file_capture(registration(), replace(request(), declared_filename="x" * 501))
    with pytest.raises(GatewayFileCaptureError, match="committed representation"):
        build_file_capture(registration(), request(), maximum_committed_bytes=32)
