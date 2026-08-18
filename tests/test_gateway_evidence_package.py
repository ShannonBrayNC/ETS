from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.microsoft_reconciliation import (
    MicrosoftReconciliationGapV1,
    acknowledge_microsoft_reconciliation_gap,
    begin_microsoft_reconciliation,
    open_microsoft_reconciliation_gap,
    resolve_microsoft_reconciliation,
)
from ets.core import (
    EvidenceEvent,
    EvidenceProofBundle,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    generate_inclusion_proof,
)
from ets.gateway.evidence_package import (
    ConnectorGapDeclarationV1,
    ConnectorSourceProvenanceV1,
    GatewayEvidencePackageV1,
    microsoft_gap_declaration,
    verify_gateway_evidence_package,
)
from ets.verifier import verify_inclusion

NOW = datetime(2026, 8, 18, 4, 30, tzinfo=UTC)
TENANT = "tenant-authoritative"
WORKSPACE = "workspace-authoritative"
CONNECTOR_ID = "microsoft.sharepoint.onedrive_delta"
SOURCE_ID = "microsoft-sharepoint-source"
SOURCE_SYSTEM = "microsoft.sharepoint.onedrive_delta"
SOURCE_RECORD = "sharepoint-record-001"
TRANSFORMATION = "ets.connector.microsoft.sharepoint-onedrive-metadata.v1"
INSTANCE = "microsoft-sharepoint-prod"


def _event(
    *,
    connector_instance_id: str | None = INSTANCE,
    raw_source_payload_retained: bool = False,
    observed_at_utc: datetime = NOW,
    capture_source_system: str = SOURCE_SYSTEM,
) -> EvidenceEvent:
    capture_metadata: dict[str, object] = {
        "connector_source_system": capture_source_system,
        "connector_source_record_id": SOURCE_RECORD,
        "connector_transformation_profile": TRANSFORMATION,
        "raw_source_payload_retained": raw_source_payload_retained,
    }
    if connector_instance_id is not None:
        capture_metadata["connector_instance_id"] = connector_instance_id
    return EvidenceEvent(
        event_id="evt-sharepoint-001",
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        evidence_id="evidence-sharepoint-001",
        event_type="microsoft.sharepoint.metadata.observed",
        subject_ref=None,
        content_hash="d" * 64,
        content_hash_alg="sha256",
        metadata={
            "capture_schema_version": "ets.capture.v1",
            "adapter_id": CONNECTOR_ID,
            "source": {
                "identifier": SOURCE_ID,
                "sequence": None,
                "idempotency_key": "connector:fixture",
                "transport_identity": "gateway-connector",
                "declared_identity": None,
            },
            "capture_metadata": capture_metadata,
        },
        created_at_utc=observed_at_utc,
        source_system=SOURCE_SYSTEM,
        correlation_id="notification-001",
    )


def _bundle(
    *,
    connector_instance_id: str | None = INSTANCE,
    raw_source_payload_retained: bool = False,
    observed_at_utc: datetime = NOW,
    tree_head_created_at_utc: datetime = NOW,
    capture_source_system: str = SOURCE_SYSTEM,
) -> EvidenceProofBundle:
    log = InMemoryAppendOnlyLog()
    entry = log.append(
        _event(
            connector_instance_id=connector_instance_id,
            raw_source_payload_retained=raw_source_payload_retained,
            observed_at_utc=observed_at_utc,
            capture_source_system=capture_source_system,
        )
    )
    proof = generate_inclusion_proof(log.list_entries(), 0)
    tree_head = SignedTreeHead(
        tree_size=1,
        root_hash=proof.root_hash,
        created_at_utc=tree_head_created_at_utc,
        log_id="ets-package-test",
    )
    return EvidenceProofBundle(
        event=entry.event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=tree_head,
        inclusion_proof=proof,
        verification_result=verify_inclusion(proof),
    )


def _provenance(**overrides: str) -> ConnectorSourceProvenanceV1:
    provenance = ConnectorSourceProvenanceV1(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        connector_id=CONNECTOR_ID,
        connector_instance_id=INSTANCE,
        source_id=SOURCE_ID,
        source_system=SOURCE_SYSTEM,
        source_record_id=SOURCE_RECORD,
        transformation_profile=TRANSFORMATION,
    )
    return provenance.model_copy(update=overrides)


def _acknowledged_gap() -> MicrosoftReconciliationGapV1:
    possible = open_microsoft_reconciliation_gap(
        gap_id="gap-001",
        instance_id=INSTANCE,
        source_system=SOURCE_SYSTEM,
        reason="missed_notification",
        detected_at_utc=NOW - timedelta(minutes=5),
        note="operator-only note that must not be exported",
    )
    reconciling = begin_microsoft_reconciliation(
        possible,
        started_at_utc=NOW - timedelta(minutes=4),
    )
    partial = resolve_microsoft_reconciliation(
        reconciling,
        outcome="partial",
        resolved_at_utc=NOW - timedelta(minutes=2),
        recovered_records=3,
    )
    acknowledged, _audit = acknowledge_microsoft_reconciliation_gap(
        partial,
        actor_id="operator@example.test",
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        acknowledged_at_utc=NOW - timedelta(minutes=1),
    )
    return acknowledged


def _package(
    *,
    bundle: EvidenceProofBundle | None = None,
    provenance: ConnectorSourceProvenanceV1 | None = None,
    gaps: tuple[ConnectorGapDeclarationV1, ...] | None = None,
) -> GatewayEvidencePackageV1:
    declarations = (
        (microsoft_gap_declaration(_acknowledged_gap()),)
        if gaps is None
        else gaps
    )
    return GatewayEvidencePackageV1(
        proof_bundle=bundle or _bundle(),
        source_provenance=provenance or _provenance(),
        gap_declarations=declarations,
        exported_at_utc=NOW + timedelta(minutes=1),
    )


def test_package_binds_committed_connector_provenance_and_verifies_embedded_proof() -> None:
    package = _package()

    result = verify_gateway_evidence_package(package)

    assert result.valid is True
    assert result.reason == "ok"
    assert package.source_provenance.connector_instance_id == INSTANCE
    assert package.source_provenance.raw_source_payload_retained is False
    assert package.verification_claimed_by_operational_declarations is False
    assert package.source_truth_claimed is False
    assert package.source_completeness_claimed is False


def test_operational_gap_declarations_do_not_change_cryptographic_verification() -> None:
    package = _package()
    declaration = package.gap_declarations[0]
    alternate = declaration.model_copy(
        update={
            "reason": "worker_outage",
            "status": "unrecoverable",
            "outcome": "unrecoverable",
            "recovered_records": 0,
        }
    )
    changed = GatewayEvidencePackageV1(
        proof_bundle=package.proof_bundle,
        source_provenance=package.source_provenance,
        gap_declarations=(alternate,),
        exported_at_utc=package.exported_at_utc,
    )

    original_result = verify_gateway_evidence_package(package)
    changed_result = verify_gateway_evidence_package(changed)

    assert original_result.valid is True
    assert changed_result.valid is True
    assert original_result.reason == changed_result.reason == "ok"
    assert original_result.root_hash == changed_result.root_hash
    assert original_result.leaf_hash == changed_result.leaf_hash
    assert original_result.tree_size == changed_result.tree_size


def test_tampered_embedded_proof_fails_regardless_of_operational_declarations() -> None:
    valid_bundle = _bundle()
    tampered = valid_bundle.model_copy(update={"event_hash": "0" * 64})
    package = _package(bundle=tampered)

    result = verify_gateway_evidence_package(package)

    assert result.valid is False
    assert result.reason == "bundle event hash does not match event"


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("tenant_id", "other-tenant", "tenant/workspace"),
        ("workspace_id", "other-workspace", "tenant/workspace"),
        ("connector_id", "other.connector", "connector_id"),
        ("connector_instance_id", "other-instance", "instance_id"),
        ("source_id", "other-source", "source_id"),
        ("source_system", "other.source", "source_system"),
        ("source_record_id", "other-record", "source_record_id"),
        ("transformation_profile", "other.profile", "transformation profile"),
    ],
)
def test_provenance_mismatch_fails_closed(field: str, value: str, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        _package(provenance=_provenance(**{field: value}))


def test_capture_metadata_source_system_conflict_fails_closed() -> None:
    bundle = _bundle(capture_source_system="other.source")

    with pytest.raises(ValidationError, match="conflicts with capture metadata"):
        _package(bundle=bundle)


def test_committed_instance_provenance_cannot_be_omitted_from_package() -> None:
    provenance = _provenance().model_copy(update={"connector_instance_id": None})

    with pytest.raises(ValidationError, match="instance_id"):
        _package(provenance=provenance, gaps=())


def test_package_rejects_connector_event_that_retained_raw_source_payload() -> None:
    with pytest.raises(ValidationError, match="no-raw-payload"):
        _package(bundle=_bundle(raw_source_payload_retained=True))


def test_gap_declaration_source_instance_and_export_time_fail_closed() -> None:
    declaration = microsoft_gap_declaration(_acknowledged_gap())
    wrong_source = declaration.model_copy(update={"source_system": "other.source"})
    with pytest.raises(ValidationError, match="source_system"):
        _package(gaps=(wrong_source,))

    wrong_instance = declaration.model_copy(update={"instance_id": "other-instance"})
    with pytest.raises(ValidationError, match="instance_id"):
        _package(gaps=(wrong_instance,))

    future_time = NOW + timedelta(hours=2)
    future = ConnectorGapDeclarationV1(
        gap_id="gap-future",
        instance_id=INSTANCE,
        source_system=SOURCE_SYSTEM,
        reason="worker_outage",
        status="possible",
        detected_at_utc=future_time,
        updated_at_utc=future_time,
    )
    with pytest.raises(ValidationError, match="detected after package export"):
        _package(gaps=(future,))


def test_duplicate_gap_id_fails_closed() -> None:
    declaration = microsoft_gap_declaration(_acknowledged_gap())
    conflicting = declaration.model_copy(update={"reason": "worker_outage"})

    with pytest.raises(ValidationError, match="duplicate connector gap_id"):
        _package(gaps=(declaration, conflicting))


def test_gap_update_timestamp_cannot_precede_lifecycle_state() -> None:
    with pytest.raises(ValidationError, match="update precedes lifecycle state"):
        ConnectorGapDeclarationV1(
            gap_id="gap-stale-update",
            instance_id=INSTANCE,
            source_system=SOURCE_SYSTEM,
            reason="worker_outage",
            status="reconciling",
            detected_at_utc=NOW - timedelta(minutes=5),
            updated_at_utc=NOW - timedelta(minutes=4),
            reconciliation_started_at_utc=NOW - timedelta(minutes=3),
        )


def test_package_export_snapshot_rejects_future_tree_or_gap_state() -> None:
    package = _package()

    future_bundle = _bundle(tree_head_created_at_utc=NOW + timedelta(minutes=2))
    with pytest.raises(ValidationError, match="export precedes proof tree head"):
        GatewayEvidencePackageV1(
            proof_bundle=future_bundle,
            source_provenance=package.source_provenance,
            gap_declarations=(),
            exported_at_utc=NOW + timedelta(minutes=1),
        )

    future_gap = package.gap_declarations[0].model_copy(
        update={"updated_at_utc": NOW + timedelta(minutes=2)}
    )
    with pytest.raises(ValidationError, match="updated after package export"):
        GatewayEvidencePackageV1(
            proof_bundle=package.proof_bundle,
            source_provenance=package.source_provenance,
            gap_declarations=(future_gap,),
            exported_at_utc=NOW + timedelta(minutes=1),
        )


def test_package_preserves_future_source_observation_with_clock_skew() -> None:
    future_observation = NOW + timedelta(minutes=5)
    bundle = _bundle(observed_at_utc=future_observation)

    package = _package(bundle=bundle)

    assert package.proof_bundle.event.created_at_utc == future_observation
    assert package.exported_at_utc < future_observation
    assert verify_gateway_evidence_package(package).valid is True


def test_gap_declaration_requires_event_bound_instance_provenance() -> None:
    legacy_bundle = _bundle(connector_instance_id=None)
    provenance = _provenance().model_copy(update={"connector_instance_id": None})

    with pytest.raises(ValidationError, match="event-bound connector instance"):
        _package(bundle=legacy_bundle, provenance=provenance)


def test_legacy_or_direct_package_without_instance_can_verify_without_gaps() -> None:
    legacy_bundle = _bundle(connector_instance_id=None)
    provenance = _provenance().model_copy(update={"connector_instance_id": None})

    package = _package(bundle=legacy_bundle, provenance=provenance, gaps=())

    assert verify_gateway_evidence_package(package).valid is True
    assert package.source_provenance.connector_instance_id is None


def test_microsoft_gap_projection_is_minimized_and_preserves_continuity_outcome() -> None:
    gap = _acknowledged_gap()

    declaration = microsoft_gap_declaration(gap)
    payload = declaration.model_dump(mode="json")

    assert declaration.status == "acknowledged"
    assert declaration.outcome == "partial"
    assert declaration.recovered_records == 3
    assert declaration.source_completeness_claimed is False
    assert declaration.affects_cryptographic_verification is False
    assert "acknowledged_by" not in payload
    assert "note" not in payload
    assert "operator@example.test" not in declaration.model_dump_json()
    assert "operator-only note" not in declaration.model_dump_json()


def test_nonclaim_flags_are_literal_false() -> None:
    declaration = microsoft_gap_declaration(_acknowledged_gap()).model_dump(mode="json")
    declaration["source_completeness_claimed"] = True
    with pytest.raises(ValidationError):
        ConnectorGapDeclarationV1.model_validate(declaration)

    package = _package().model_dump(mode="json")
    package["source_truth_claimed"] = True
    with pytest.raises(ValidationError):
        GatewayEvidencePackageV1.model_validate(package)
