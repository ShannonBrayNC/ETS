from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import JsonValue

from ets.connectors.enterprise.microsoft_sharepoint_state import SharePointMetadataStateStore
from ets.connectors.models import (
    ConnectorCheckpointV1,
    ConnectorCollectionResultV1,
    ConnectorEvidenceCandidateV1,
)
from ets.connectors.runtime import ConnectorOperationReceiptV1
from ets.gateway.connector_capture import GatewayConnectorCandidateRequest
from ets.gateway.connector_runner import GatewayConnectorCollectionRunner
from ets.gateway.microsoft_sharepoint_state_release import (
    SharePointMetadataStateReleaseHook,
    SharePointMetadataTransitionCandidateHook,
)

NOW = datetime(2026, 8, 14, 20, 30, tzinfo=UTC)
SOURCE_KEY = "tenant-authoritative/workspace-authoritative/sharepoint-authoritative"
DONE_CHECKPOINT = (
    "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$deltatoken=done"
)


def _record(source_record_id: str, name: str) -> dict[str, JsonValue]:
    return {
        "source_record_id": source_record_id,
        "object_id": "item-001",
        "scope": "drive",
        "deleted": False,
        "source_modified_at_utc": "2026-08-14T20:30:00Z",
        "metadata": {
            "name": name,
            "size": 1234,
            "parent": {"id": "folder-001", "drive_id": "drive-001"},
        },
    }


def _candidate(record: dict[str, JsonValue]) -> ConnectorEvidenceCandidateV1:
    return ConnectorEvidenceCandidateV1(
        schema_version="ets.connector.candidate.v1",
        source_record_id=str(record["source_record_id"]),
        source_system="microsoft.sharepoint.onedrive_delta",
        observed_at_utc=NOW,
        event_type="microsoft.sharepoint.metadata.observed",
        media_type="application/json",
        transformation_profile="ets.connector.microsoft.sharepoint-onedrive-metadata.v1",
        lossless=False,
        metadata={
            "provider": "microsoft",
            "source_class": "sharepoint_onedrive_metadata_delta",
            "cloud": "global",
            "scope": record["scope"],
            "object_id": record["object_id"],
            "deleted": record["deleted"],
            "metadata": record["metadata"],
        },
    )


class FixtureInstance:
    instance_id = "sharepoint-fixture"


class FixtureAdapter:
    def __init__(self, record: dict[str, JsonValue]) -> None:
        self.record = record

    def collect(self, instance: object, checkpoint: object) -> ConnectorCollectionResultV1:
        del instance, checkpoint
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=(self.record,),
            checkpoint=ConnectorCheckpointV1(
                schema_version="ets.connector.checkpoint.v1",
                cursor=DONE_CHECKPOINT,
            ),
            has_more=False,
            message="fixture page",
        )

    def normalize(
        self,
        instance: object,
        record: dict[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        del instance
        return _candidate(record)


class FixtureIngress:
    def __init__(self) -> None:
        self.candidates: list[ConnectorEvidenceCandidateV1] = []
        self.requests: list[GatewayConnectorCandidateRequest] = []

    def ingest_candidate(
        self,
        principal: str,
        request: GatewayConnectorCandidateRequest,
    ) -> ConnectorOperationReceiptV1:
        del principal
        self.candidates.append(request.candidate)
        self.requests.append(request)
        return ConnectorOperationReceiptV1(
            schema_version="ets.connector.operation_receipt.v1",
            instance_id="sharepoint-fixture",
            stage="sync_queued",
            source_received=True,
            committed_local=True,
            sync_queued=True,
            sync_acknowledged=False,
            created_at_utc=NOW,
        )


def test_candidate_classification_precedes_commit_and_state_release_follows_queue(
    tmp_path: Path,
) -> None:
    store = SharePointMetadataStateStore(tmp_path / "state.db")
    candidate_hook = SharePointMetadataTransitionCandidateHook(store, source_key=SOURCE_KEY)
    release_hook = SharePointMetadataStateReleaseHook(store, source_key=SOURCE_KEY)
    ingress = FixtureIngress()
    runner = GatewayConnectorCollectionRunner(ingress)
    instance = FixtureInstance()
    baseline_adapter = FixtureAdapter(_record("drive:item-001:baseline", "report.docx"))

    baseline = runner.run(
        adapter=baseline_adapter,
        instance=instance,
        principal="fixture-principal",
        checkpoint=None,
        candidate_hook=candidate_hook,
        release_hook=release_hook,
    )

    assert baseline.code == "ok"
    assert ingress.requests[0].connector_instance_id == "sharepoint-fixture"
    first_claim = ingress.candidates[0].metadata["derived_transition"]
    assert isinstance(first_claim, dict)
    assert first_claim["kinds"] == ["baseline_observation"]
    persisted = store.get(SOURCE_KEY, "drive", "item-001")
    assert persisted is not None
    assert persisted.name == "report.docx"
    assert store.baseline_complete(SOURCE_KEY) is True

    renamed_adapter = FixtureAdapter(_record("drive:item-001:renamed", "renamed.docx"))
    renamed = runner.run(
        adapter=renamed_adapter,
        instance=instance,
        principal="fixture-principal",
        checkpoint=baseline.checkpoint_to_persist,
        candidate_hook=candidate_hook,
        release_hook=release_hook,
    )

    assert renamed.code == "ok"
    assert ingress.requests[1].connector_instance_id == "sharepoint-fixture"
    second_claim = ingress.candidates[1].metadata["derived_transition"]
    assert isinstance(second_claim, dict)
    assert second_claim["kinds"] == ["renamed"]
    persisted = store.get(SOURCE_KEY, "drive", "item-001")
    assert persisted is not None
    assert persisted.name == "renamed.docx"
