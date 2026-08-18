from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCapabilities,
    ConnectorCollection,
    ConnectorConfigurationSchema,
    ConnectorDefinitionV1,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime_store import ConnectorRuntimeStore
from ets.core import (
    EvidenceEvent,
    EvidenceProofBundle,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    generate_inclusion_proof,
)
from ets.gateway.connector_management import (
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.connector_management_api import create_connector_management_router
from ets.gateway.evidence_package import (
    ConnectorSourceProvenanceV1,
    GatewayEvidencePackageV1,
    verify_gateway_evidence_package,
)
from ets.runtime.sync_queue import SyncQueue
from ets.runtime.sync_queue_scope import GATEWAY_SYNC_SCHEMA, source_scoped_sync_queue_status
from ets.verifier import verify_inclusion

NOW = datetime(2026, 8, 18, 5, 30, tzinfo=UTC)
CONNECTOR_ID = "microsoft.sharepoint.onedrive_delta"
SOURCE_SYSTEM = CONNECTOR_ID
SOURCE_ID = "microsoft-sharepoint-source"
TENANT_A = "tenant-a"
WORKSPACE_A = "workspace-a"
TENANT_B = "tenant-b"
WORKSPACE_B = "workspace-b"
INSTANCE_A = "sharepoint-a"
INSTANCE_B = "sharepoint-b"


def _definition() -> ConnectorDefinitionV1:
    return ConnectorDefinitionV1(
        schema_version="ets.connector.definition.v1",
        connector_id=CONNECTOR_ID,
        display_name="Microsoft SharePoint / OneDrive",
        description="Synthetic multi-tenant qualification definition.",
        implementation_class="enterprise_api",
        source_classes=("microsoft", "sharepoint"),
        adapter_version="1.0",
        sdk_contract_version="ets.connector.sdk.v1",
        capture_envelope_versions=("ets.capture.v1",),
        gateway_host_versions=("ets.gateway.connector-host.v1",),
        capabilities=ConnectorCapabilities(
            delivery_modes=("poll",),
            authentication_methods=("bearer",),
            checkpointing=True,
            reconciliation=True,
        ),
        configuration_schema=ConnectorConfigurationSchema(
            instance_schema="ets.connector.instance.v1"
        ),
    )


def _instance(
    instance_id: str,
    *,
    tenant_id: str,
    workspace_id: str,
) -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=instance_id,
        connector_id=CONNECTOR_ID,
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id=tenant_id, workspace_id=workspace_id),
        source=ConnectorSource(name=instance_id, environment="qualification"),
        authentication=ConnectorAuthentication(
            method="bearer",
            credential_ref=f"secret://{instance_id}",
        ),
        collection=ConnectorCollection(mode="poll", interval_seconds=60),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.microsoft.sharepoint.v1",
            normalization_profile="ets.connector.microsoft.sharepoint-onedrive-metadata.v1",
        ),
        settings={},
    )


def _principal(
    tenant_id: str,
    workspace_id: str,
) -> ConnectorManagementPrincipal:
    return ConnectorManagementPrincipal(
        actor_id=f"operator-{tenant_id}",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        can_read=True,
        can_manage=True,
    )


def _management_client(tmp_path: Path) -> tuple[TestClient, ConnectorManagementService]:
    management = ConnectorManagementService(
        registry=ConnectorRegistry([_definition()]),
        store=ConnectorRuntimeStore(tmp_path / "connector-runtime.db"),
        now=lambda: NOW,
    )
    management.create_instance(
        _principal(TENANT_A, WORKSPACE_A),
        _instance(INSTANCE_A, tenant_id=TENANT_A, workspace_id=WORKSPACE_A),
    )
    management.create_instance(
        _principal(TENANT_B, WORKSPACE_B),
        _instance(INSTANCE_B, tenant_id=TENANT_B, workspace_id=WORKSPACE_B),
    )

    def resolve(request: Request) -> ConnectorManagementPrincipal:
        return _principal(
            request.headers.get("x-tenant", TENANT_A),
            request.headers.get("x-workspace", WORKSPACE_A),
        )

    app = FastAPI()
    app.include_router(create_connector_management_router(management, resolve))
    return TestClient(app), management


def _gateway_payload(
    key: str,
    *,
    tenant_id: str,
    workspace_id: str,
) -> dict[str, object]:
    return {
        "sync_schema": GATEWAY_SYNC_SCHEMA,
        "idempotency_key": key,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "event_id": f"event-{key}",
        "event_hash": f"hash-{key}",
        "log_index": 1,
        "capture": {
            "source_id": SOURCE_ID,
            "content_hash": f"content-{key}",
            "content_hash_alg": "sha256",
        },
        "raw_payload_included": False,
    }


def _bundle(
    *,
    tenant_id: str,
    workspace_id: str,
    source_record_id: str,
) -> EvidenceProofBundle:
    event = EvidenceEvent(
        event_id=f"evt-{source_record_id}",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        evidence_id=f"evidence-{source_record_id}",
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
                "idempotency_key": f"connector:{source_record_id}",
                "transport_identity": "gateway-connector",
                "declared_identity": None,
            },
            "capture_metadata": {
                "connector_source_system": SOURCE_SYSTEM,
                "connector_source_record_id": source_record_id,
                "connector_transformation_profile": (
                    "ets.connector.microsoft.sharepoint-onedrive-metadata.v1"
                ),
                "raw_source_payload_retained": False,
            },
        },
        created_at_utc=NOW,
        source_system=SOURCE_SYSTEM,
        correlation_id=None,
    )
    log = InMemoryAppendOnlyLog()
    entry = log.append(event)
    proof = generate_inclusion_proof(log.list_entries(), 0)
    return EvidenceProofBundle(
        event=event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=SignedTreeHead(
            tree_size=1,
            root_hash=proof.root_hash,
            created_at_utc=NOW,
            log_id=f"log-{tenant_id}",
        ),
        inclusion_proof=proof,
        verification_result=verify_inclusion(proof),
    )


def _package(
    bundle: EvidenceProofBundle,
    *,
    tenant_id: str,
    workspace_id: str,
    source_record_id: str,
) -> GatewayEvidencePackageV1:
    return GatewayEvidencePackageV1(
        proof_bundle=bundle,
        source_provenance=ConnectorSourceProvenanceV1(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            connector_id=CONNECTOR_ID,
            source_id=SOURCE_ID,
            source_system=SOURCE_SYSTEM,
            source_record_id=source_record_id,
            transformation_profile="ets.connector.microsoft.sharepoint-onedrive-metadata.v1",
        ),
        exported_at_utc=NOW,
    )


def test_connector_management_api_and_runtime_store_are_tenant_isolated(tmp_path: Path) -> None:
    api, management = _management_client(tmp_path)
    headers_a = {"x-tenant": TENANT_A, "x-workspace": WORKSPACE_A}
    headers_b = {"x-tenant": TENANT_B, "x-workspace": WORKSPACE_B}

    list_a = api.get("/gateway/connectors/v1/instances", headers=headers_a)
    list_b = api.get("/gateway/connectors/v1/instances", headers=headers_b)

    assert list_a.status_code == 200
    assert list_b.status_code == 200
    assert [item["instance"]["instance_id"] for item in list_a.json()["items"]] == [INSTANCE_A]
    assert [item["instance"]["instance_id"] for item in list_b.json()["items"]] == [INSTANCE_B]

    cross_get = api.get(
        f"/gateway/connectors/v1/instances/{INSTANCE_B}",
        headers=headers_a,
    )
    cross_runtime = api.get(
        f"/gateway/connectors/v1/instances/{INSTANCE_B}/runtime",
        headers=headers_a,
    )
    cross_mutation = api.post(
        f"/gateway/connectors/v1/instances/{INSTANCE_B}/gaps/detect",
        headers=headers_a,
    )

    assert cross_get.status_code == 403
    assert cross_runtime.status_code == 403
    assert cross_mutation.status_code == 403
    assert management.get_runtime(_principal(TENANT_B, WORKSPACE_B), INSTANCE_B).gap_open is False


def test_shared_sync_queue_isolates_same_source_id_by_tenant_and_workspace(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "shared-sync.db")
    record_a = queue.enqueue(
        _gateway_payload("tenant-a", tenant_id=TENANT_A, workspace_id=WORKSPACE_A)
    )
    record_b = queue.enqueue(
        _gateway_payload("tenant-b", tenant_id=TENANT_B, workspace_id=WORKSPACE_B)
    )
    queue.mark_retryable(record_a.idempotency_key, "tenant A retryable failure")
    queue.mark_terminal(record_b.idempotency_key, "tenant B terminal failure")

    status_a = source_scoped_sync_queue_status(
        queue,
        tenant_id=TENANT_A,
        workspace_id=WORKSPACE_A,
        source_id=SOURCE_ID,
        now=NOW,
    )
    status_b = source_scoped_sync_queue_status(
        queue,
        tenant_id=TENANT_B,
        workspace_id=WORKSPACE_B,
        source_id=SOURCE_ID,
        now=NOW,
    )

    assert status_a.retryable_failure == 1
    assert status_a.terminal_failure == 0
    assert status_a.latest_active_failure is not None
    assert "tenant A retryable failure" in status_a.latest_active_failure
    assert status_b.retryable_failure == 0
    assert status_b.terminal_failure == 1
    assert status_b.latest_active_failure is not None
    assert "tenant B terminal failure" in status_b.latest_active_failure


def test_evidence_packages_bind_provenance_to_each_tenant_proof() -> None:
    bundle_a = _bundle(
        tenant_id=TENANT_A,
        workspace_id=WORKSPACE_A,
        source_record_id="record-a",
    )
    bundle_b = _bundle(
        tenant_id=TENANT_B,
        workspace_id=WORKSPACE_B,
        source_record_id="record-b",
    )
    package_a = _package(
        bundle_a,
        tenant_id=TENANT_A,
        workspace_id=WORKSPACE_A,
        source_record_id="record-a",
    )
    package_b = _package(
        bundle_b,
        tenant_id=TENANT_B,
        workspace_id=WORKSPACE_B,
        source_record_id="record-b",
    )

    assert verify_gateway_evidence_package(package_a).valid is True
    assert verify_gateway_evidence_package(package_b).valid is True
    assert TENANT_B not in package_a.model_dump_json()
    assert WORKSPACE_B not in package_a.model_dump_json()
    assert TENANT_A not in package_b.model_dump_json()
    assert WORKSPACE_A not in package_b.model_dump_json()

    with pytest.raises(ValidationError, match="tenant/workspace"):
        _package(
            bundle_a,
            tenant_id=TENANT_B,
            workspace_id=WORKSPACE_B,
            source_record_id="record-a",
        )
