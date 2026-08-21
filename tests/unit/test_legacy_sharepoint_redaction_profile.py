from __future__ import annotations

from datetime import UTC, datetime

import pytest

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


def test_legacy_sharepoint_profile_preserves_immutable_event_exactly() -> None:
    event = _event(redaction_profile="microsoft_sharepoint_metadata_v1")

    result = apply_redaction_profile(event, "strict")

    assert result is event
    assert result.model_dump(mode="json") == event.model_dump(mode="json")
    assert result.hashable_payload() == event.hashable_payload()
    assert result.redaction_profile == "microsoft_sharepoint_metadata_v1"
    assert (
        result.metadata["capture_metadata"]["committed_connector_metadata"]["metadata"][
            "email"
        ]
        == "already-minimized@example.invalid"
    )


def test_legacy_profile_is_bound_to_sharepoint_source() -> None:
    event = _event(
        redaction_profile="microsoft_sharepoint_metadata_v1",
        source_system="untrusted.connector",
    )

    with pytest.raises(ValueError, match="unsupported redaction profile"):
        apply_redaction_profile(event)


def test_unknown_connector_profile_still_fails_closed() -> None:
    event = _event(redaction_profile="unregistered_connector_profile_v1")

    with pytest.raises(ValueError, match="unsupported redaction profile"):
        apply_redaction_profile(event)
