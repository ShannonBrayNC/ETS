from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ets.connectors.enterprise.microsoft_health import MicrosoftOperationalPostureV1
from ets.qualification import microsoft_soak_probe as probe_module

NOW = datetime(2026, 8, 18, 7, 0, tzinfo=UTC)
TENANT = "tenant-authoritative"
WORKSPACE = "workspace-authoritative"
INSTANCE = "microsoft-sharepoint-prod"
SOURCE_SHA = "a" * 40
IMAGE_DIGEST = f"sha256:{'b' * 64}"


def _posture() -> MicrosoftOperationalPostureV1:
    return MicrosoftOperationalPostureV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.operational_posture.v1",
            "instance_id": INSTANCE,
            "ets_tenant_id": TENANT,
            "workspace_id": WORKSPACE,
            "source_id": "microsoft-sharepoint-source",
            "microsoft_tenant_id": "11111111-1111-1111-1111-111111111111",
            "subscription_id": "subscription-001",
            "evaluated_at_utc": NOW,
            "policy_profile_id": "microsoft-p0-demo",
            "health": {
                "schema_version": "ets.connector.health.v1",
                "state": "healthy",
                "code": "ok",
                "message": "Microsoft source is reachable",
            },
            "subscription_status": "active",
            "subscription_expiration_date_time": NOW + timedelta(days=3),
            "seconds_until_subscription_expiration": 3 * 24 * 60 * 60,
            "collection_lag_seconds": 60.0,
            "queue_depth": 0,
            "oldest_unsynchronized_age_seconds": None,
            "retryable_failure_count": 0,
            "terminal_failure_count": 0,
            "reconciliation_status": None,
            "reconciliation_outcome": None,
            "verification_claimed": False,
            "source_truth_claimed": False,
            "completeness_claimed": False,
        }
    )


def _args() -> argparse.Namespace:
    return argparse.Namespace(
        core_base_url="https://core.example.test",
        management_base_url="https://management.example.test",
        instance_id=INSTANCE,
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        source_sha=SOURCE_SHA,
        image_digest=IMAGE_DIGEST,
        workflow_run_id="32100000000",
        output=None,
    )


def test_management_posture_uses_server_derived_scope_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        calls.append((method, url, kwargs))
        if url.endswith("/api/v2/auth/context"):
            return {
                "tenant_id": TENANT,
                "workspace_id": WORKSPACE,
                "capabilities": ["connector.read"],
            }
        return _posture().model_dump(mode="json")

    monkeypatch.setattr(probe_module, "_request_json", fake_request)

    posture = probe_module._read_management_posture(
        "https://management.example.test",
        "management-token",
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        instance_id=INSTANCE,
    )

    assert posture.instance_id == INSTANCE
    assert len(calls) == 2
    for _method, _url, kwargs in calls:
        assert kwargs["token"] == "management-token"
        assert "tenant_id" not in kwargs
        assert "workspace_id" not in kwargs


def test_management_scope_mismatch_fails_before_posture_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {
            "tenant_id": "other-tenant",
            "workspace_id": WORKSPACE,
            "capabilities": ["connector.read"],
        }

    monkeypatch.setattr(probe_module, "_request_json", fake_request)

    with pytest.raises(RuntimeError, match="auth context does not match"):
        probe_module._read_management_posture(
            "https://management.example.test",
            "management-token",
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            instance_id=INSTANCE,
        )
    assert calls == 1


def test_core_scope_uses_server_derived_scope_only(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        calls.append((method, url, kwargs))
        return {"tenant_id": TENANT, "workspace_id": WORKSPACE}

    monkeypatch.setattr(probe_module, "_request_json", fake_request)

    probe_module._require_core_auth_scope(
        "https://core.example.test",
        "core-token",
        TENANT,
        WORKSPACE,
    )

    assert len(calls) == 1
    _method, _url, kwargs = calls[0]
    assert kwargs["token"] == "core-token"
    assert "tenant_id" not in kwargs
    assert "workspace_id" not in kwargs


def test_core_proof_requests_use_server_derived_scope_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        calls.append((method, url, kwargs))
        if url.endswith("/api/v1/events"):
            return {"event_hash": "a" * 64}
        if "/api/v1/proofs/inclusion/" in url:
            return {"synthetic": "proof"}
        if url.endswith("/api/v1/verify/inclusion"):
            return {"valid": True}
        raise AssertionError(f"unexpected URL {url}")

    class FakeInclusionProof:
        @classmethod
        def model_validate(cls, payload: dict[str, Any]) -> dict[str, Any]:
            return payload

    class ValidResult:
        valid = True

    monkeypatch.setattr(probe_module, "_request_json", fake_request)
    monkeypatch.setattr(probe_module, "InclusionProof", FakeInclusionProof)
    monkeypatch.setattr(probe_module, "verify_inclusion_proof", lambda _proof: ValidResult())

    proof_reference, proof_valid = probe_module._append_and_verify_probe_proof(
        "https://core.example.test",
        "core-token",
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        workflow_run_id="32100000000",
        collected_at=NOW,
    )

    assert proof_reference.startswith("/api/v1/proofs/inclusion/")
    assert proof_valid is True
    assert len(calls) == 3
    for _method, _url, kwargs in calls:
        assert kwargs["token"] == "core-token"
        assert "tenant_id" not in kwargs
        assert "workspace_id" not in kwargs


def test_collect_probe_retains_no_bearer_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core_token = "core-secret-token"
    management_token = "management-secret-token"
    monkeypatch.setenv(probe_module.CORE_TOKEN_ENV, core_token)
    monkeypatch.setenv(probe_module.MANAGEMENT_TOKEN_ENV, management_token)
    monkeypatch.setattr(probe_module, "_require_core_ready", lambda _url: None)

    core_scope_tokens: list[str] = []
    management_tokens: list[str] = []
    proof_tokens: list[str] = []

    def fake_core_scope(
        _base_url: str,
        token: str,
        _tenant_id: str,
        _workspace_id: str,
    ) -> None:
        core_scope_tokens.append(token)

    def fake_posture(
        _base_url: str,
        token: str,
        **_kwargs: Any,
    ) -> MicrosoftOperationalPostureV1:
        management_tokens.append(token)
        return _posture()

    def fake_proof(
        _base_url: str,
        token: str,
        **_kwargs: Any,
    ) -> tuple[str, bool]:
        proof_tokens.append(token)
        return "/api/v1/proofs/inclusion/g2e-f-soak-32100000000", True

    monkeypatch.setattr(probe_module, "_require_core_auth_scope", fake_core_scope)
    monkeypatch.setattr(probe_module, "_read_management_posture", fake_posture)
    monkeypatch.setattr(probe_module, "_append_and_verify_probe_proof", fake_proof)

    probe = probe_module.collect_probe(_args())
    serialized = probe.model_dump_json()

    assert core_scope_tokens == [core_token]
    assert management_tokens == [management_token]
    assert proof_tokens == [core_token]
    assert core_token not in serialized
    assert management_token not in serialized
    assert probe.proof_reference.startswith("/api/v1/proofs/inclusion/")
    assert "core.example.test" not in serialized
    assert "management.example.test" not in serialized
    assert probe.reusable_credential_retained is False
    assert probe.raw_source_payload_retained is False


def test_synthetic_event_is_bounded_non_customer_qualification_data() -> None:
    event = probe_module._synthetic_event(
        "32100000000",
        TENANT,
        WORKSPACE,
        NOW,
    )

    assert event["event_type"] == "qualification.microsoft_soak"
    assert event["tenant_id"] == TENANT
    assert event["workspace_id"] == WORKSPACE
    metadata = event["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["synthetic"] is True
    assert metadata["contains_real_pii"] is False
    assert metadata["raw_customer_evidence"] is False
    assert len(str(event["content_hash"])) == 64


def test_core_scope_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        return {"tenant_id": TENANT, "workspace_id": "other-workspace"}

    monkeypatch.setattr(probe_module, "_request_json", fake_request)

    with pytest.raises(RuntimeError, match="auth context does not match"):
        probe_module._require_core_auth_scope(
            "https://core.example.test",
            "core-token",
            TENANT,
            WORKSPACE,
        )
