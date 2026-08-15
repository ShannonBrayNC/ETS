from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import JsonValue

from ets.connectors.enterprise.microsoft_sharepoint_state import (
    MicrosoftSharePointStateError,
    SharePointMetadataStateStore,
    snapshot_sharepoint_metadata_record,
)
from ets.connectors.models import ConnectorEvidenceCandidateV1
from ets.gateway.connector_capture import GatewayConnectorCandidateRequest, build_connector_capture
from ets.gateway.microsoft_sharepoint_state_release import (
    SHAREPOINT_TRANSITION_CLAIM_SCHEMA,
    SharePointMetadataTransitionCandidateHook,
)
from ets.gateway.source_registry import SourceRegistration

NOW = datetime(2026, 8, 14, 20, 30, tzinfo=UTC)
SOURCE_KEY = "tenant-authoritative/workspace-authoritative/sharepoint-authoritative"


def _record(
    *,
    source_record_id: str = "drive:item-001:baseline",
    name: str = "report.docx",
    parent_id: str = "folder-001",
) -> dict[str, JsonValue]:
    return {
        "source_record_id": source_record_id,
        "object_id": "item-001",
        "scope": "drive",
        "deleted": False,
        "source_modified_at_utc": "2026-08-14T20:30:00Z",
        "metadata": {
            "name": name,
            "size": 1234,
            "parent": {"id": parent_id, "drive_id": "drive-001"},
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


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal="spiffe://example.test/workload/microsoft-sharepoint",
        source_id="sharepoint-authoritative",
        source_system="microsoft.sharepoint.onedrive_delta",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id="microsoft.sharepoint.onedrive_delta",
        adapter_version="1.0",
        event_type="microsoft.sharepoint.metadata.observed",
        classification="internal",
        redaction_profile="sharepoint-metadata-redaction-v1",
        minimization_profile="sharepoint-metadata-only-v1",
        clock_quality="unknown",
    )


def test_transition_claim_preserves_observation_without_advancing_operational_state(
    tmp_path: Path,
) -> None:
    store = SharePointMetadataStateStore(tmp_path / "state.db")
    record = _record()
    candidate = _candidate(record)
    hook = SharePointMetadataTransitionCandidateHook(store, source_key=SOURCE_KEY)

    enriched = hook.transform(record, candidate)

    assert store.get(SOURCE_KEY, "drive", "item-001") is None
    assert store.baseline_complete(SOURCE_KEY) is False
    assert enriched.metadata["metadata"] == record["metadata"]
    claim = enriched.metadata["derived_transition"]
    assert isinstance(claim, dict)
    assert claim["schema_version"] == SHAREPOINT_TRANSITION_CLAIM_SCHEMA
    assert claim["claim_type"] == "derived_metadata_transition"
    assert claim["basis"] == "successive_minimized_metadata_observations"
    assert claim["kinds"] == ["baseline_observation"]
    assert claim["prior_metadata_sha256"] is None

    capture = build_connector_capture(
        _registration(),
        GatewayConnectorCandidateRequest(candidate=enriched, received_at_utc=NOW),
    )
    committed = json.loads(capture.committed_representation)
    committed_metadata = committed["metadata"]
    assert committed_metadata["metadata"] == record["metadata"]
    assert committed_metadata["derived_transition"] == claim
    assert "actor" not in json.dumps(claim, sort_keys=True).casefold()


def test_successive_committed_state_supports_bounded_rename_claim(tmp_path: Path) -> None:
    store = SharePointMetadataStateStore(tmp_path / "state.db")
    baseline = _record()
    store.apply(
        SOURCE_KEY,
        [snapshot_sharepoint_metadata_record(baseline)],
        mark_baseline_complete=True,
    )
    changed = _record(
        source_record_id="drive:item-001:renamed",
        name="renamed.docx",
    )
    hook = SharePointMetadataTransitionCandidateHook(store, source_key=SOURCE_KEY)

    enriched = hook.transform(changed, _candidate(changed))

    claim = enriched.metadata["derived_transition"]
    assert isinstance(claim, dict)
    assert claim["kinds"] == ["renamed"]
    assert isinstance(claim["prior_metadata_sha256"], str)
    assert isinstance(claim["current_metadata_sha256"], str)
    persisted = store.get(SOURCE_KEY, "drive", "item-001")
    assert persisted is not None
    assert persisted.name == "report.docx"


def test_transition_hook_rejects_candidate_that_does_not_preserve_observed_metadata(
    tmp_path: Path,
) -> None:
    store = SharePointMetadataStateStore(tmp_path / "state.db")
    record = _record()
    candidate = _candidate(record)
    tampered_metadata = dict(candidate.metadata)
    tampered_metadata["object_id"] = "different-item"
    tampered = candidate.model_copy(update={"metadata": tampered_metadata})
    hook = SharePointMetadataTransitionCandidateHook(store, source_key=SOURCE_KEY)

    with pytest.raises(MicrosoftSharePointStateError, match="object does not match"):
        hook.transform(record, tampered)
