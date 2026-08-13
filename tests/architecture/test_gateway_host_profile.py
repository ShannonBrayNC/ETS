from __future__ import annotations

import json
from pathlib import Path

from ets.gateway.host import GatewayHostPolicy

PROFILE_PATH = Path("config/gateway/http-host-profile.v1.json")


def test_gateway_host_profile_matches_runtime_defaults() -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    limits = profile["request_limits"]
    policy = GatewayHostPolicy()

    assert limits["max_header_count"] == policy.max_header_count
    assert limits["max_header_bytes"] == policy.max_header_bytes
    assert limits["max_header_value_bytes"] == policy.max_header_value_bytes
    assert limits["max_concurrent_requests"] == policy.max_concurrent_requests
    assert limits["admission_timeout_seconds"] == policy.admission_timeout_seconds
    assert limits["body_read_timeout_seconds"] == policy.body_read_timeout_seconds
    assert tuple(limits["allowed_content_encodings"]) == policy.allowed_content_encodings


def test_gateway_host_profile_preserves_non_inline_and_logging_boundaries() -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    assert profile["schema_version"] == "ets.gateway.http_host.v1"
    assert profile["network_role"] == "out_of_band"
    assert profile["inline_network_dependency"] is False
    assert profile["logging"]["credential_values"] is False
    assert profile["logging"]["raw_payload"] is False
    assert profile["timeout_boundary"]["body_read_is_cancellable_pre_commit"] is True
    assert profile["timeout_boundary"]["authoritative_append_is_inside_request_timeout"] is False
