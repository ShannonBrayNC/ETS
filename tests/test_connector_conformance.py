from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import JsonValue, ValidationError

from ets.connectors.conformance import ConnectorConformanceHarness
from ets.connectors.models import (
    ConnectorCheckpointV1,
    ConnectorCollectionResultV1,
    ConnectorDefinitionV1,
    ConnectorEvidenceCandidateV1,
    ConnectorHealthV1,
    ConnectorInstanceV1,
    ConnectorReconciliationResultV1,
)
from ets.connectors.registry import ConnectorRegistry

ROOT = Path(__file__).parents[1]
EXAMPLES = ROOT / "schemas" / "connectors" / "v1" / "examples"
FIXTURES = ROOT / "tests" / "fixtures" / "connectors" / "v1"


class SyntheticAdapter:
    def __init__(self) -> None:
        self._definition = ConnectorDefinitionV1.model_validate_json(
            (EXAMPLES / "connector-definition.synthetic.json").read_text(encoding="utf-8")
        )

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        if instance.settings.get("stream") != "primary":
            raise ValueError("stream must be primary")

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.health(instance)

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        return ()

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=(),
            checkpoint=checkpoint,
        )

    def checkpoint(self, result: ConnectorCollectionResultV1) -> ConnectorCheckpointV1 | None:
        return result.checkpoint

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorReconciliationResultV1:
        return ConnectorReconciliationResultV1(
            schema_version="ets.connector.reconciliation_result.v1",
            code="ok",
            reconciled=True,
            gap_detected=False,
            checkpoint=checkpoint,
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: dict[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        record_id = record.get("record_id")
        assert isinstance(record_id, str)
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id=record_id,
            source_system="synthetic-audit",
            observed_at_utc=None,
            event_type="audit.synthetic",
            transformation_profile=instance.policy.normalization_profile,
            lossless=True,
            metadata={"action": record.get("action")},
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="healthy",
            code="ok",
            message="synthetic connector ready",
        )


def test_conformance_harness_accepts_shared_contract() -> None:
    adapter = SyntheticAdapter()
    registry = ConnectorRegistry()
    registry.register_adapter(adapter)
    instance = ConnectorInstanceV1.model_validate_json(
        (EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8")
    )
    record = json.loads((FIXTURES / "source-record.synthetic.json").read_text(encoding="utf-8"))
    report = ConnectorConformanceHarness(registry).validate_sample(adapter, instance, record)
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_candidate_boundary_rejects_authoritative_scope_and_proof_fields() -> None:
    with pytest.raises(ValidationError):
        ConnectorEvidenceCandidateV1.model_validate(
            {
                "schema_version": "ets.connector.candidate.v1",
                "source_record_id": "r-1",
                "source_system": "synthetic-audit",
                "observed_at_utc": None,
                "event_type": "audit.synthetic",
                "transformation_profile": "synthetic.audit.v1",
                "lossless": True,
                "metadata": {},
                "tenant_id": "attacker-supplied",
                "workspace_id": "attacker-supplied",
                "tree_head": "not-allowed",
            }
        )
