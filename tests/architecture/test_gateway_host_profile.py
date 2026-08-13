from __future__ import annotations

import json
from pathlib import Path

from ets.gateway.host import GatewayHostPolicy

PROFILE_PATH = Path("config/gateway/http-host-profile.v1.json")


def test_gateway_host_profile_matches_runtime_defaults() -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    limits = profile["request_limits"]
    critical = limits["critical_header_value_bytes"]
    policy = GatewayHostPolicy()

    assert limits["max_header_count"] == policy.max_header_count
    assert limits["max_header_bytes"] == policy.max_header_bytes
    assert limits["max_header_value_bytes"] == policy.max_header_value_bytes
    assert critical["content-type"] == policy.max_content_type_bytes
    assert critical["x-ets-observed-at"] == policy.max_observed_at_bytes
    assert critical["idempotency-key"] == policy.max_idempotency_key_bytes
    assert critical["x-ets-declared-identity"] == policy.max_declared_identity_bytes
    assert critical["x-correlation-id"] == policy.max_correlation_id_bytes
    assert critical["content-encoding"] == policy.max_content_encoding_bytes
    assert critical["authorization"] == policy.max_authorization_bytes
    assert critical["content-length"] == policy.max_content_length_bytes
    assert limits["security_relevant_headers_are_singleton"] is True
    assert limits["max_concurrent_requests"] == policy.max_concurrent_requests
    assert limits["admission_timeout_seconds"] == policy.admission_timeout_seconds
    assert limits["body_read_timeout_seconds"] == policy.body_read_timeout_seconds
    assert tuple(limits["allowed_content_encodings"]) == policy.allowed_content_encodings


def test_gateway_host_profile_preserves_non_inline_logging_and_shutdown_boundaries() -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    shutdown = profile["shutdown"]

    assert profile["schema_version"] == "ets.gateway.http_host.v1"
    assert profile["network_role"] == "out_of_band"
    assert profile["inline_network_dependency"] is False
    assert profile["logging"]["credential_values"] is False
    assert profile["logging"]["raw_payload"] is False
    assert profile["timeout_boundary"]["body_read_is_cancellable_pre_commit"] is True
    assert profile["timeout_boundary"]["authoritative_append_is_inside_request_timeout"] is False
    assert shutdown["drain_is_one_way"] is True
    assert shutdown["new_requests_rejected_after_drain_begins"] is True
    assert shutdown["already_admitted_requests_complete"] is True
    assert shutdown["waiting_requests_recheck_drain_after_capacity_acquisition"] is True
    assert shutdown["wait_drained_available"] is True
    assert shutdown["fresh_worker_controller_accepts_after_restart"] is True
