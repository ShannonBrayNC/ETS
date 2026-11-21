from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.configuration_monitor_archive import (
    BaselineReplacementRequestV1,
    ConfigurationMonitorArchiveProfileV1,
    ConfigurationMonitorArchiveV1,
    EmergencyArchiveApprovalV1,
    PaginatedArchiveV1,
    assess_baseline_replacement,
)

NOW = datetime(2026, 11, 21, 2, 0, tzinfo=UTC)
REQUESTED = NOW - timedelta(minutes=1)
PRIOR_BASELINE_BYTES = b'{"setting":"old"}'
PROPOSED_BASELINE_BYTES = b'{"setting":"new"}'
DECISION_BYTES = b'{"decision":"approved_standard"}'
OLD_BASELINE = hashlib.sha256(PRIOR_BASELINE_BYTES).hexdigest()
NEW_BASELINE = hashlib.sha256(PROPOSED_BASELINE_BYTES).hexdigest()
DECISION = hashlib.sha256(DECISION_BYTES).hexdigest()


def _profile() -> dict[str, object]:
    return {
        "schema_version": "ets.microsoft.configuration_monitor_archive.v1",
        "profile_id": "configuration-monitor-pilot-001",
        "tenant_id": "tenant-a",
        "monitor_id": "monitor-a",
        "archive_max_age_seconds": 3600,
        "request_authorities": ("app:configuration-change-requestor",),
        "emergency_approval_authorities": ("group:emergency-change-approvers",),
        "required_monitor_fields": (
            "id",
            "displayName",
            "baseline",
            "parameters",
            "createdDateTime",
            "lastModifiedDateTime",
        ),
        "required_run_fields": ("id", "status", "startedDateTime", "completedDateTime"),
        "required_result_fields": ("id", "runId", "resource", "status", "observedValue"),
        "required_drift_fields": ("id", "resultId", "property", "expected", "actual"),
        "service_limits": {
            "documentation_url": "https://learn.microsoft.com/example/config-monitor-limits",
            "documented_at_utc": NOW - timedelta(days=1),
            "minimum_evaluation_interval_seconds": 3600,
            "maximum_evaluations_per_day": 24,
            "result_retention_seconds": 30 * 86_400,
        },
        "evaluation_policy": {
            "evaluation_interval_seconds": 3600,
            "scheduled_evaluations_per_day": 24,
            "archive_lookback_seconds": 7 * 86_400,
            "polling_interval_seconds": 300,
            "freshness_source": "evaluation_completed_at",
            "polling_establishes_freshness": False,
        },
    }


def _payloads() -> dict[str, bytes]:
    return {
        "objects/monitor.json": b'{"id":"monitor-a"}',
        "objects/prior-baseline.json": PRIOR_BASELINE_BYTES,
        "objects/parameters.json": b'{"scope":"pilot"}',
        "objects/proposed-baseline.json": PROPOSED_BASELINE_BYTES,
        "objects/decision.json": DECISION_BYTES,
        "collections/runs-1.json": b'{"value":[{"id":"run-1"}]}',
        "collections/runs-2.json": b'{"value":[{"id":"run-2"}]}',
        "collections/results-1.json": b'{"value":[{"id":"result-1"}]}',
        "collections/drifts-1.json": b'{"value":[]}',
    }


def _file(path: str, payloads: dict[str, bytes]) -> dict[str, object]:
    value = payloads[path]
    return {
        "path": path,
        "byte_length": len(value),
        "sha256": hashlib.sha256(value).hexdigest(),
    }


def _archive(payloads: dict[str, bytes] | None = None) -> dict[str, object]:
    payloads = payloads or _payloads()
    return {
        "schema_version": "ets.microsoft.configuration_monitor_archive.v1",
        "profile_id": "configuration-monitor-pilot-001",
        "tenant_id": "tenant-a",
        "monitor_id": "monitor-a",
        "prior_baseline_sha256": OLD_BASELINE,
        "proposed_baseline_sha256": NEW_BASELINE,
        "decision": "approved_standard",
        "decision_record_sha256": DECISION,
        "last_evaluation_completed_at_utc": REQUESTED - timedelta(minutes=20),
        "export_started_at_utc": REQUESTED - timedelta(minutes=15),
        "export_completed_at_utc": REQUESTED - timedelta(minutes=10),
        "monitor_fields": _profile()["required_monitor_fields"],
        "objects": (
            {"logical_name": "monitor_definition", **_file("objects/monitor.json", payloads)},
            {
                "logical_name": "prior_baseline",
                **_file("objects/prior-baseline.json", payloads),
            },
            {"logical_name": "parameters", **_file("objects/parameters.json", payloads)},
            {
                "logical_name": "proposed_baseline",
                **_file("objects/proposed-baseline.json", payloads),
            },
            {"logical_name": "decision_record", **_file("objects/decision.json", payloads)},
        ),
        "collections": (
            {
                "collection": "runs",
                "exported_fields": _profile()["required_run_fields"],
                "total_record_count": 2,
                "expected_page_count": 2,
                "pages": (
                    {
                        "page_number": 1,
                        "record_count": 1,
                        "next_cursor_sha256": "d" * 64,
                        **_file("collections/runs-1.json", payloads),
                    },
                    {
                        "page_number": 2,
                        "record_count": 1,
                        "next_cursor_sha256": None,
                        **_file("collections/runs-2.json", payloads),
                    },
                ),
            },
            {
                "collection": "results",
                "exported_fields": _profile()["required_result_fields"],
                "total_record_count": 1,
                "expected_page_count": 1,
                "pages": (
                    {
                        "page_number": 1,
                        "record_count": 1,
                        "next_cursor_sha256": None,
                        **_file("collections/results-1.json", payloads),
                    },
                ),
            },
            {
                "collection": "drifts",
                "exported_fields": _profile()["required_drift_fields"],
                "total_record_count": 0,
                "expected_page_count": 1,
                "pages": (
                    {
                        "page_number": 1,
                        "record_count": 0,
                        "next_cursor_sha256": None,
                        **_file("collections/drifts-1.json", payloads),
                    },
                ),
            },
        ),
    }


def _request(*, emergency: bool = False) -> BaselineReplacementRequestV1:
    return BaselineReplacementRequestV1.model_validate(
        {
            "request_id": "change-001",
            "profile_id": "configuration-monitor-pilot-001",
            "tenant_id": "tenant-a",
            "monitor_id": "monitor-a",
            "requestor_identity": "app:configuration-change-requestor",
            "prior_baseline_sha256": OLD_BASELINE,
            "proposed_baseline_sha256": NEW_BASELINE,
            "decision": "approved_standard",
            "decision_record_sha256": DECISION,
            "requested_at_utc": REQUESTED,
            "emergency": emergency,
        }
    )


def _approval() -> EmergencyArchiveApprovalV1:
    return EmergencyArchiveApprovalV1.model_validate(
        {
            "approval_id": "emergency-approval-001",
            "request_id": "change-001",
            "profile_id": "configuration-monitor-pilot-001",
            "tenant_id": "tenant-a",
            "monitor_id": "monitor-a",
            "approver_identity": "group:emergency-change-approvers",
            "prior_baseline_sha256": OLD_BASELINE,
            "proposed_baseline_sha256": NEW_BASELINE,
            "decision": "approved_standard",
            "decision_record_sha256": DECISION,
            "archive_exception": True,
            "reason": "Restore service while the archive endpoint is unavailable",
            "approved_at_utc": REQUESTED - timedelta(minutes=1),
            "expires_at_utc": NOW + timedelta(minutes=5),
        }
    )


def test_profile_pins_service_limits_and_separates_polling_from_freshness() -> None:
    profile = ConfigurationMonitorArchiveProfileV1.model_validate(_profile())

    assert profile.evaluation_policy.polling_establishes_freshness is False
    assert profile.evaluation_policy.freshness_source == "evaluation_completed_at"
    assert not set(profile.request_authorities) & set(profile.emergency_approval_authorities)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("evaluation_interval_seconds", 1800, "faster than"),
        ("scheduled_evaluations_per_day", 25, "daily quota"),
        ("archive_lookback_seconds", 31 * 86_400, "result retention"),
        ("polling_establishes_freshness", True, "Input should be False"),
    ],
)
def test_profile_rejects_service_policy_violations(
    field: str, value: object, message: str
) -> None:
    payload = deepcopy(_profile())
    policy = payload["evaluation_policy"]
    assert isinstance(policy, dict)
    policy[field] = value

    with pytest.raises(ValidationError, match=message):
        ConfigurationMonitorArchiveProfileV1.model_validate(payload)


def test_paginated_archive_requires_every_ordered_page_and_terminal_cursor() -> None:
    group = deepcopy(_archive()["collections"][0])  # type: ignore[index]
    assert isinstance(group, dict)
    pages = group["pages"]
    assert isinstance(pages, tuple)
    group["pages"] = (pages[1],)

    with pytest.raises(ValidationError, match="missing one or more pages"):
        PaginatedArchiveV1.model_validate(group)

    group = deepcopy(_archive()["collections"][0])  # type: ignore[index]
    assert isinstance(group, dict)
    pages = group["pages"]
    assert isinstance(pages, tuple)
    pages[1]["next_cursor_sha256"] = "e" * 64

    with pytest.raises(ValidationError, match="final runs page"):
        PaginatedArchiveV1.model_validate(group)


def test_verified_complete_archive_allows_replacement() -> None:
    profile = ConfigurationMonitorArchiveProfileV1.model_validate(_profile())
    payloads = _payloads()
    archive = ConfigurationMonitorArchiveV1.model_validate(_archive(payloads))

    result = assess_baseline_replacement(
        profile,
        _request(),
        archive,
        archive_bytes=payloads,
        evaluated_at_utc=NOW,
    )

    assert result.verdict == "allowed"
    assert result.reason == "archive_verified"
    assert result.archive_completed_at_utc == archive.export_completed_at_utc


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing", "archive_bytes_missing"),
        ("altered", "archive_digest_mismatch"),
    ],
)
def test_missing_or_altered_archive_bytes_block_replacement(
    mutation: str, reason: str
) -> None:
    profile = ConfigurationMonitorArchiveProfileV1.model_validate(_profile())
    payloads = _payloads()
    archive = ConfigurationMonitorArchiveV1.model_validate(_archive(payloads))
    if mutation == "missing":
        del payloads["collections/results-1.json"]
    else:
        payloads["objects/prior-baseline.json"] = b'{"setting":"tampered"}'

    result = assess_baseline_replacement(
        profile,
        _request(),
        archive,
        archive_bytes=payloads,
        evaluated_at_utc=NOW,
    )

    assert result.verdict == "blocked"
    assert result.reason == reason


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("decision", "repair"),
        ("monitor_fields", ("id",)),
    ],
)
def test_archive_must_bind_baselines_decision_and_complete_fields(
    field: str, value: object
) -> None:
    profile = ConfigurationMonitorArchiveProfileV1.model_validate(_profile())
    payload = deepcopy(_archive())
    payload[field] = value
    archive = ConfigurationMonitorArchiveV1.model_validate(payload)

    result = assess_baseline_replacement(
        profile,
        _request(),
        archive,
        archive_bytes=_payloads(),
        evaluated_at_utc=NOW,
    )

    assert result.verdict == "blocked"
    assert result.reason == "archive_binding_mismatch"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("prior_baseline_sha256", "f" * 64, "prior baseline bytes"),
        ("proposed_baseline_sha256", "f" * 64, "proposed baseline bytes"),
        ("decision_record_sha256", "f" * 64, "decision record bytes"),
    ],
)
def test_archive_digests_must_derive_from_their_exact_bytes(
    field: str, value: str, message: str
) -> None:
    payload = deepcopy(_archive())
    payload[field] = value

    with pytest.raises(ValidationError, match=message):
        ConfigurationMonitorArchiveV1.model_validate(payload)


def test_archive_older_than_gate_window_blocks_replacement() -> None:
    profile = ConfigurationMonitorArchiveProfileV1.model_validate(_profile())
    payload = deepcopy(_archive())
    payload["last_evaluation_completed_at_utc"] = REQUESTED - timedelta(hours=3)
    payload["export_started_at_utc"] = REQUESTED - timedelta(hours=2)
    payload["export_completed_at_utc"] = REQUESTED - timedelta(hours=2)
    archive = ConfigurationMonitorArchiveV1.model_validate(payload)

    result = assess_baseline_replacement(
        profile,
        _request(),
        archive,
        archive_bytes=_payloads(),
        evaluated_at_utc=NOW,
    )

    assert result.reason == "archive_too_old"


def test_evaluation_outside_reviewed_lookback_blocks_replacement() -> None:
    profile_payload = deepcopy(_profile())
    policy = profile_payload["evaluation_policy"]
    assert isinstance(policy, dict)
    policy["archive_lookback_seconds"] = 3600
    profile = ConfigurationMonitorArchiveProfileV1.model_validate(profile_payload)
    payload = deepcopy(_archive())
    payload["last_evaluation_completed_at_utc"] = REQUESTED - timedelta(hours=2)
    archive = ConfigurationMonitorArchiveV1.model_validate(payload)

    result = assess_baseline_replacement(
        profile,
        _request(),
        archive,
        archive_bytes=_payloads(),
        evaluated_at_utc=NOW,
    )

    assert result.reason == "archive_too_old"


def test_missing_archive_blocks_non_emergency_replacement() -> None:
    result = assess_baseline_replacement(
        ConfigurationMonitorArchiveProfileV1.model_validate(_profile()),
        _request(),
        None,
        archive_bytes={},
        evaluated_at_utc=NOW,
    )

    assert result.verdict == "blocked"
    assert result.reason == "archive_missing"


def test_separately_authorized_emergency_exception_is_explicit() -> None:
    result = assess_baseline_replacement(
        ConfigurationMonitorArchiveProfileV1.model_validate(_profile()),
        _request(emergency=True),
        None,
        archive_bytes={},
        evaluated_at_utc=NOW,
        emergency_approval=_approval(),
    )

    assert result.verdict == "emergency_exception"
    assert result.reason == "emergency_approval_recorded"
    assert result.emergency_approval_id == "emergency-approval-001"


def test_emergency_replacement_without_approval_stays_blocked() -> None:
    result = assess_baseline_replacement(
        ConfigurationMonitorArchiveProfileV1.model_validate(_profile()),
        _request(emergency=True),
        None,
        archive_bytes={},
        evaluated_at_utc=NOW,
    )

    assert result.verdict == "blocked"
    assert result.reason == "emergency_approval_missing"


def test_expired_or_cross_request_emergency_approval_stays_blocked() -> None:
    profile = ConfigurationMonitorArchiveProfileV1.model_validate(_profile())
    approval_payload = _approval().model_dump()
    approval_payload["expires_at_utc"] = NOW - timedelta(seconds=1)
    expired = EmergencyArchiveApprovalV1.model_validate(approval_payload)
    result = assess_baseline_replacement(
        profile,
        _request(emergency=True),
        None,
        archive_bytes={},
        evaluated_at_utc=NOW,
        emergency_approval=expired,
    )
    assert result.reason == "emergency_approval_expired"

    approval_payload = _approval().model_dump()
    approval_payload["request_id"] = "different-change"
    mismatched = EmergencyArchiveApprovalV1.model_validate(approval_payload)
    result = assess_baseline_replacement(
        profile,
        _request(emergency=True),
        None,
        archive_bytes={},
        evaluated_at_utc=NOW,
        emergency_approval=mismatched,
    )
    assert result.reason == "emergency_approval_binding_mismatch"
