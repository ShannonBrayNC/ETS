from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from pydantic import JsonValue

from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCapabilities,
    ConnectorCollection,
    ConnectorCollectionResultV1,
    ConnectorConfigurationSchema,
    ConnectorDefinitionV1,
    ConnectorEvidenceCandidateV1,
    ConnectorHealthV1,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorReconciliationResultV1,
    ConnectorScope,
    ConnectorSource,
)
from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.connector_capture import (
    GatewayConnectorCandidateRequest,
    build_connector_capture,
)
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.connector_runner import GatewayConnectorCollectionRunner
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue

NOW = datetime(2026, 8, 18, 5, 20, tzinfo=UTC)
CONNECTOR_ID = "synthetic.poll"
INSTANCE_ID = "synthetic-instance-a"
SOURCE_ID = "authoritative-source-a"
SOURCE_SYSTEM = "synthetic.source"
PRINCIPAL = "spiffe://example.test/workload/synthetic-connector"


class SyntheticAdapter:
    @property
    def definition(self) -> ConnectorDefinitionV1:
        return _definition()

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        return None

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.health(instance)

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        return (instance.source.name,)

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: object,
    ) -> ConnectorCollectionResultV1:
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=({"record_id": "record-001"},),
        )

    def checkpoint(self, result: ConnectorCollectionResultV1) -> None:
        return None

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: object,
    ) -> ConnectorReconciliationResultV1:
        return ConnectorReconciliationResultV1(
            schema_version="ets.connector.reconciliation_result.v1",
            code="ok",
            reconciled=True,
            gap_detected=False,
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        return _candidate()

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="healthy",
            code="ok",
            message="synthetic source is reachable",
        )


def _definition() -> ConnectorDefinitionV1:
    return ConnectorDefinitionV1(
        schema_version="ets.connector.definition.v1",
        connector_id=CONNECTOR_ID,
        display_name="Synthetic Poll",
        description="Synthetic adapter used to qualify connector instance provenance.",
        implementation_class="generic",
        source_classes=("synthetic",),
        adapter_version="1.0",
        sdk_contract_version="ets.connector.sdk.v1",
        capture_envelope_versions=("ets.capture.v1",),
        gateway_host_versions=("ets.gateway.connector-host.v1",),
        capabilities=ConnectorCapabilities(
            delivery_modes=("poll",),
            authentication_methods=("none",),
            checkpointing=True,
            reconciliation=True,
        ),
        configuration_schema=ConnectorConfigurationSchema(
            instance_schema="ets.connector.instance.v1"
        ),
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=INSTANCE_ID,
        connector_id=CONNECTOR_ID,
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(
            tenant_id="instance-scope-is-not-authority",
            workspace_id="instance-workspace-is-not-authority",
        ),
        source=ConnectorSource(name="synthetic-source", environment="test"),
        authentication=ConnectorAuthentication(method="none", credential_ref=None),
        collection=ConnectorCollection(mode="poll", interval_seconds=60, batch_size=10),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.synthetic.v1",
            normalization_profile="normalize.synthetic.v1",
        ),
        settings={},
    )


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id=SOURCE_ID,
        source_system=SOURCE_SYSTEM,
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id=CONNECTOR_ID,
        adapter_version="1.0",
        event_type="synthetic.observed",
        classification="internal",
        redaction_profile="synthetic-redaction-v1",
        minimization_profile="synthetic-minimization-v1",
        clock_quality="unknown",
    )


def _candidate() -> ConnectorEvidenceCandidateV1:
    return ConnectorEvidenceCandidateV1(
        schema_version="ets.connector.candidate.v1",
        source_record_id="record-001",
        source_system=SOURCE_SYSTEM,
        observed_at_utc=NOW,
        event_type="synthetic.observed",
        media_type="application/json",
        transformation_profile="synthetic.v1",
        lossless=False,
        metadata={"name": "qualification-record"},
    )


def test_runner_commits_instance_id_into_hashed_event_provenance(tmp_path: Path) -> None:
    event_log = InMemoryAppendOnlyLog()
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "sync.db"),
        now=lambda: NOW,
    )
    runner = GatewayConnectorCollectionRunner(ingress)

    result = runner.run(
        adapter=SyntheticAdapter(),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert result.code == "ok"
    entries = event_log.list_entries()
    assert len(entries) == 1
    event = entries[0].event
    capture_metadata = event.metadata["capture_metadata"]
    assert isinstance(capture_metadata, dict)
    assert capture_metadata["connector_instance_id"] == INSTANCE_ID
    assert event.metadata["source"]["identifier"] == SOURCE_ID
    assert INSTANCE_ID != SOURCE_ID


def test_instance_provenance_does_not_change_connector_content_identity() -> None:
    without_instance = build_connector_capture(
        _registration(),
        GatewayConnectorCandidateRequest(candidate=_candidate(), received_at_utc=NOW),
    )
    with_instance = build_connector_capture(
        _registration(),
        GatewayConnectorCandidateRequest(
            candidate=_candidate(),
            connector_instance_id=INSTANCE_ID,
            received_at_utc=NOW,
        ),
    )

    assert without_instance.committed_representation == with_instance.committed_representation
    assert (
        without_instance.envelope.content_digest.value
        == with_instance.envelope.content_digest.value
    )
    assert "connector_instance_id" not in without_instance.envelope.metadata
    assert with_instance.envelope.metadata["connector_instance_id"] == INSTANCE_ID
