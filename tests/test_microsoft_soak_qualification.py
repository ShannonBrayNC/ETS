from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.connectors.enterprise.microsoft_health import MicrosoftOperationalPostureV1
from ets.connectors.models import ConnectorHealthV1
from ets.qualification.microsoft_soak import (
    MicrosoftSoakPolicyV1,
    MicrosoftSoakProbeV1,
    MicrosoftSoakQualificationError,
    summarize_microsoft_soak,
)

START = datetime(2026, 8, 18, 6, 0, tzinfo=UTC)
SOURCE_SHA = "a" * 40
IMAGE_DIGEST = f"sha256:{'b' * 64}"


def _policy() -> MicrosoftSoakPolicyV1:
    return MicrosoftSoakPolicyV1(
        profile_id="microsoft-p0-72h-hourly",
        minimum_duration_seconds=72 * 60 * 60,
        minimum_probe_count=73,
        maximum_probe_interval_seconds=90 * 60,
        maximum_evaluation_age_seconds=5 * 60,
    )


def _posture(
    instant: datetime,
    *,
    state: str = "healthy",
    code: str = "ok",
    instance_id: str = "microsoft-sharepoint-prod",
    subscription_id: str = "subscription-001",
    terminal_failure_count: int = 0,
) -> MicrosoftOperationalPostureV1:
    return MicrosoftOperationalPostureV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.operational_posture.v1",
            "instance_id": instance_id,
            "ets_tenant_id": "tenant-authoritative",
            "workspace_id": "workspace-authoritative",
            "source_id": "microsoft-sharepoint-source",
            "microsoft_tenant_id": "11111111-1111-1111-1111-111111111111",
            "subscription_id": subscription_id,
            "evaluated_at_utc": instant,
            "policy_profile_id": "microsoft-p0-demo",
            "health": ConnectorHealthV1.model_validate(
                {
                    "schema_version": "ets.connector.health.v1",
                    "state": state,
                    "code": code,
                    "message": f"fixture posture is {state}",
                }
            ),
            "subscription_status": "active",
            "subscription_expiration_date_time": instant + timedelta(days=3),
            "seconds_until_subscription_expiration": 3 * 24 * 60 * 60,
            "collection_lag_seconds": 60.0,
            "queue_depth": 0,
            "oldest_unsynchronized_age_seconds": None,
            "retryable_failure_count": 0,
            "terminal_failure_count": terminal_failure_count,
            "reconciliation_status": None,
            "reconciliation_outcome": None,
            "verification_claimed": False,
            "source_truth_claimed": False,
            "completeness_claimed": False,
        }
    )


def _probe(
    instant: datetime,
    *,
    posture: MicrosoftOperationalPostureV1 | None = None,
    source_sha: str = SOURCE_SHA,
    proof_verification_valid: bool = True,
) -> MicrosoftSoakProbeV1:
    return MicrosoftSoakProbeV1(
        source_sha=source_sha,
        image_digest=IMAGE_DIGEST,
        workflow_run_id=f"run-{int(instant.timestamp())}",
        collected_at_utc=instant,
        posture=posture or _posture(instant),
        proof_reference=f"probe/{instant.isoformat()}",
        proof_verification_valid=proof_verification_valid,
    )


def _hourly_probes() -> tuple[MicrosoftSoakProbeV1, ...]:
    return tuple(_probe(START + timedelta(hours=offset)) for offset in range(73))


def test_full_72_hour_hourly_window_qualifies() -> None:
    summary = summarize_microsoft_soak(_hourly_probes(), _policy())

    assert summary.qualified is True
    assert summary.duration_seconds == 72 * 60 * 60
    assert summary.probe_count == 73
    assert summary.maximum_observed_probe_interval_seconds == 60 * 60
    assert summary.healthy_probe_count == 73
    assert summary.degraded_probe_count == 0
    assert summary.failed_probe_count == 0
    assert summary.proof_failure_count == 0
    assert summary.subscription_id == "subscription-001"
    assert summary.blockers == ()
    assert summary.verification_claimed_by_soak is False
    assert summary.source_truth_claimed is False
    assert summary.source_completeness_claimed is False


def test_missing_probe_interval_blocks_qualification() -> None:
    probes = tuple(
        probe
        for index, probe in enumerate(_hourly_probes())
        if index not in {20, 21}
    )

    summary = summarize_microsoft_soak(probes, _policy())

    assert summary.qualified is False
    assert summary.maximum_observed_probe_interval_seconds == 3 * 60 * 60
    assert "soak probe interval exceeds policy" in summary.blockers
    assert "soak probe count is below policy" in summary.blockers


def test_degraded_or_terminal_operational_probe_blocks_release() -> None:
    probes = list(_hourly_probes())
    instant = START + timedelta(hours=12)
    probes[12] = _probe(
        instant,
        posture=_posture(
            instant,
            state="degraded",
            code="terminal_error",
            terminal_failure_count=1,
        ),
    )

    summary = summarize_microsoft_soak(tuple(probes), _policy())

    assert summary.qualified is False
    assert summary.degraded_probe_count == 1
    assert summary.terminal_failure_probe_count == 1
    assert "one or more Microsoft operational probes were degraded" in summary.blockers
    assert "one or more probes reported terminal synchronization failures" in summary.blockers


def test_proof_failure_blocks_release_without_becoming_operational_health() -> None:
    probes = list(_hourly_probes())
    probes[7] = _probe(
        START + timedelta(hours=7),
        proof_verification_valid=False,
    )

    summary = summarize_microsoft_soak(tuple(probes), _policy())

    assert summary.qualified is False
    assert summary.healthy_probe_count == 73
    assert summary.proof_failure_count == 1
    assert "one or more soak proof verifications failed" in summary.blockers


def test_release_candidate_identity_cannot_drift_during_soak() -> None:
    probes = list(_hourly_probes())
    probes[-1] = _probe(
        START + timedelta(hours=72),
        source_sha="c" * 40,
    )

    with pytest.raises(MicrosoftSoakQualificationError, match="identity changed"):
        summarize_microsoft_soak(tuple(probes), _policy())


def test_subscription_identity_cannot_drift_during_soak() -> None:
    probes = list(_hourly_probes())
    instant = START + timedelta(hours=72)
    probes[-1] = _probe(
        instant,
        posture=_posture(instant, subscription_id="subscription-replacement"),
    )

    with pytest.raises(MicrosoftSoakQualificationError, match="identity changed"):
        summarize_microsoft_soak(tuple(probes), _policy())


def test_posture_evaluation_must_be_fresh_for_probe() -> None:
    probes = list(_hourly_probes())
    collected = START + timedelta(hours=4)
    stale_posture = _posture(collected - timedelta(minutes=6))
    probes[4] = _probe(collected, posture=stale_posture)

    with pytest.raises(MicrosoftSoakQualificationError, match="too far"):
        summarize_microsoft_soak(tuple(probes), _policy())


def test_duplicate_probe_timestamp_fails_closed() -> None:
    probes = list(_hourly_probes())
    probes[-1] = probes[-2].model_copy(update={"workflow_run_id": "duplicate-run"})

    with pytest.raises(MicrosoftSoakQualificationError, match="duplicate probe timestamps"):
        summarize_microsoft_soak(tuple(probes), _policy())
