from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from ets.api.app import create_app
from ets.core.canonical_json import canonical_sha256
from ets.core.models import EvidenceEvent
from ets.core.redaction import apply_redaction_profile


def _event(
    *,
    redaction_profile: str,
    source_system: str = "microsoft.sharepoint.onedrive_delta",
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id="gateway:" + "a" * 64,
        tenant_id="tenant_demo",
        workspace_id="workspace_alpha",
        evidence_id="gateway-evidence:" + "b" * 64,
        event_type="microsoft.sharepoint.item.observed",
        subject_ref=None,
        content_hash="c" * 64,
        content_hash_alg="sha256",
        metadata={
            "capture_metadata": {
                "committed_connector_metadata": {
                    "metadata": {
                        "name": "ets-live-qualification-marker.txt",
                        "email": "already-minimized@example.invalid",
                    }
                }
            }
        },
        created_at_utc=datetime(2026, 8, 21, tzinfo=UTC),
        source_system=source_system,
        actor_id=None,
        correlation_id=None,
        external_refs=None,
        redaction_profile=redaction_profile,
    )


@pytest.mark.parametrize(
    ("source_system", "redaction_profile"),
    (
        ("microsoft.sharepoint.onedrive_delta", "microsoft_sharepoint_metadata_v1"),
        ("microsoft.entra.directory_delta", "microsoft_entra_directory_metadata_v1"),
        ("microsoft.purview.activity", "microsoft_purview_common_schema_v1"),
    ),
)
def test_server_owned_connector_profile_preserves_immutable_event_exactly(
    source_system: str,
    redaction_profile: str,
) -> None:
    event = _event(
        redaction_profile=redaction_profile,
        source_system=source_system,
    )

    result = apply_redaction_profile(event, "strict")

    assert result is event
    assert result.model_dump(mode="json") == event.model_dump(mode="json")
    assert result.hashable_payload() == event.hashable_payload()
    assert result.redaction_profile == redaction_profile
    assert (
        result.metadata["capture_metadata"]["committed_connector_metadata"]["metadata"][
            "email"
        ]
        == "already-minimized@example.invalid"
    )


@pytest.mark.parametrize(
    ("source_system", "redaction_profile"),
    (
        ("microsoft.entra.directory_delta", "microsoft_entra_directory_metadata_v1"),
        ("microsoft.purview.activity", "microsoft_purview_common_schema_v1"),
    ),
)
def test_core_append_accepts_qualified_microsoft_connector_profile_without_rehashing(
    source_system: str,
    redaction_profile: str,
) -> None:
    event = _event(
        redaction_profile=redaction_profile,
        source_system=source_system,
    )
    client = TestClient(create_app(redaction_profile="strict"))

    response = client.post("/api/v1/events", json=event.model_dump(mode="json"))

    assert response.status_code == 201
    assert response.json()["event_hash"] == canonical_sha256(event.hashable_payload())
    retained = client.get(f"/api/v1/events/{event.event_id}")
    assert retained.status_code == 200
    assert retained.json()["event"] == event.model_dump(mode="json")


@pytest.mark.parametrize(
    "redaction_profile",
    (
        "microsoft_sharepoint_metadata_v1",
        "microsoft_entra_directory_metadata_v1",
        "microsoft_purview_common_schema_v1",
    ),
)
def test_connector_profile_is_bound_to_its_server_owned_source(
    redaction_profile: str,
) -> None:
    event = _event(redaction_profile=redaction_profile, source_system="untrusted.connector")

    with pytest.raises(ValueError, match="unsupported redaction profile"):
        apply_redaction_profile(event)


def test_unknown_connector_profile_still_fails_closed() -> None:
    event = _event(redaction_profile="unregistered_connector_profile_v1")

    with pytest.raises(ValueError, match="unsupported redaction profile"):
        apply_redaction_profile(event)
