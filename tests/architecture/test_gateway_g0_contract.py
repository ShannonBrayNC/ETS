from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "config/gateway/reference-profile.v1.json"
SCHEMA_PATH = ROOT / "schemas/gateway/v1/gateway-profile.schema.json"

REQUIRED_DOCS = {
    "docs/architecture/ETS_GATEWAY_ARCHITECTURE.md",
    "docs/security/ETS_GATEWAY_THREAT_MODEL.md",
    "docs/spec/ETS_GATEWAY_PROFILE.md",
    "docs/test/ETS_GATEWAY_G0_TEST_PLAN.md",
    "docs/adr/ADR-005-ets-gateway-non-inline-default.md",
    "docs/adr/ADR-006-ets-gateway-network-zones.md",
    "docs/adr/ADR-007-ets-gateway-capture-privacy-boundary.md",
    "docs/adr/ADR-008-ets-gateway-identity-signer-time.md",
    "docs/review/ETS_GATEWAY_G0_TECH_EDIT.md",
}


def _profile() -> dict[str, object]:
    value = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _schema() -> dict[str, object]:
    value = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_gateway_profile_has_stable_identity_and_is_not_production() -> None:
    profile = _profile()
    assert profile["profile_id"] == "ets.gateway.reference.pilot.v1"
    assert profile["schema_version"] == "ets.gateway.profile.v1"
    assert profile["conformance_class"] == "pilot"


def test_gateway_default_is_out_of_band_and_inline_is_deferred() -> None:
    profile = _profile()
    deployment = profile["deployment"]
    assert isinstance(deployment, dict)
    modes = deployment["modes"]
    assert isinstance(modes, dict)
    assert deployment["default_mode"] == "collector"
    assert deployment["availability_authority"] is False
    assert modes["collector"] == {"enabled": True, "status": "normative"}
    assert modes["passive_mirror"] == {"enabled": True, "status": "experimental"}
    assert modes["routed_inline"] == {"enabled": False, "status": "deferred"}


def test_gateway_profile_forbids_interzone_forwarding() -> None:
    profile = _profile()
    controls = profile["network_controls"]
    assert isinstance(controls, dict)
    assert controls["ipv4_forwarding"] is False
    assert controls["ipv6_forwarding"] is False
    assert controls["nat"] is False
    assert controls["interzone_bridge"] is False
    assert controls["firewall_policy"] == "default_deny_explicit_allow"


def test_gateway_network_zones_separate_management_collection_and_upstream() -> None:
    profile = _profile()
    zones = profile["zones"]
    assert isinstance(zones, dict)
    management = zones["management"]
    collection = zones["collection"]
    upstream = zones["upstream"]
    observation = zones["observation"]
    assert all(isinstance(zone, dict) for zone in (management, collection, upstream, observation))
    assert management["required"] is True
    assert management["management_listener"] is True
    assert management["ingestion_listener"] is False
    assert collection["required"] is True
    assert collection["management_listener"] is False
    assert collection["ingestion_listener"] is True
    assert upstream["required"] is True
    assert upstream["management_listener"] is False
    assert upstream["ingestion_listener"] is False
    assert observation["required"] is False
    assert observation["default_route"] is False
    assert observation["management_listener"] is False
    # Passive mirror capture consumes the interface directly; it does not expose an ingress service.
    assert observation["ingestion_listener"] is False
    assert observation["sync_listener"] is False


def test_gateway_privacy_and_digest_boundary_is_explicit() -> None:
    profile = _profile()
    boundary = profile["evidence_boundary"]
    assert isinstance(boundary, dict)
    assert boundary["privacy_before_commit"] is True
    assert boundary["raw_evidence_retained"] is False
    assert boundary["digest_basis"] == "declared_evidence_representation"
    assert boundary["transformation_provenance"] is True
    assert boundary["completeness_claim"] is False


def test_gateway_uses_core_public_api_without_reimplementing_protocol() -> None:
    profile = _profile()
    boundary = profile["core_boundary"]
    assert isinstance(boundary, dict)
    assert boundary["api"] == "ets.core.api"
    assert boundary["reimplement_protocol_semantics"] is False
    assert boundary["local_history_rewritable_by_upstream"] is False


def test_gateway_tls_profile_matches_current_bcp_shape() -> None:
    profile = _profile()
    tls = profile["transport_security"]
    assert isinstance(tls, dict)
    assert set(tls["prohibited_versions"]) == {"SSLv2", "SSLv3", "TLS1.0", "TLS1.1"}
    assert tls["minimum_compatible"] == "TLS1.2"
    assert tls["preferred"] == "TLS1.3"
    assert tls["mtls_preferred"] is True


def test_gateway_syslog_profile_prefers_tls_and_marks_udp_lower_assurance() -> None:
    profile = _profile()
    protocols = profile["protocols"]
    assert isinstance(protocols, dict)
    syslog = protocols["syslog"]
    assert isinstance(syslog, dict)
    assert syslog["preferred_format"] == "RFC5424"
    assert syslog["preferred_transport"] == "TLS"
    assert syslog["tls_default_port"] == 6514
    assert syslog["udp_compatibility"] is True
    assert syslog["udp_lower_assurance"] is True
    assert syslog["transport_identity_separate_from_hostname"] is True
    # RFC 5425 contains 2009-era TLS cipher requirements; G0 uses its syslog/TLS
    # transport model while current cryptographic configuration follows BCP 195,
    # so full RFC 5425 conformance is not claimed.
    assert syslog["rfc5425_full_conformance_claim"] is False


def test_gateway_otlp_profile_declares_transport_and_signal_scope() -> None:
    profile = _profile()
    protocols = profile["protocols"]
    assert isinstance(protocols, dict)
    otlp = protocols["otlp"]
    assert isinstance(otlp, dict)
    assert set(otlp["transports"]) == {"grpc", "http/protobuf"}
    assert set(otlp["signals"]) == {"logs", "metrics", "traces"}


def test_gateway_identity_does_not_infer_identity_from_network_or_hostname() -> None:
    profile = _profile()
    identity = profile["identity"]
    assert isinstance(identity, dict)
    assert identity["network_location_is_identity"] is False
    assert identity["transport_and_payload_identity_separate"] is True
    assert identity["tenant_scope_server_authorized"] is True
    assert identity["syslog_tls_identity_equals_hostname"] is False


def test_gateway_reference_signer_and_platform_require_hardware_security() -> None:
    profile = _profile()
    signer = profile["signer"]
    platform = profile["platform"]
    assert isinstance(signer, dict)
    assert isinstance(platform, dict)
    assert signer["development_software_allowed"] is True
    assert signer["pilot_hardware_backed_required"] is True
    assert signer["private_key_exportable_to_app"] is False
    assert signer["purpose_separated_keys"] is True
    assert platform["architecture"] == "x86_64"
    assert platform["min_memory_gib"] >= 16
    assert platform["reference_memory_gib"] >= 32
    assert platform["min_nvme_gib"] >= 1024
    assert platform["tpm2_required"] is True
    assert platform["uefi_secure_boot_required"] is True
    assert platform["preferred_physical_nics"] >= 4


def test_gateway_time_profile_preserves_time_uncertainty() -> None:
    profile = _profile()
    time = profile["time"]
    assert isinstance(time, dict)
    assert time["source_and_receipt_time_separate"] is True
    assert time["monotonic_for_durations"] is True
    assert time["ntpv4_supported"] is True
    assert time["nts_preferred"] is True
    assert time["clock_quality_required"] is True
    assert time["authenticated_time_proves_correct_utc"] is False


def test_gateway_resource_limits_and_observability_do_not_silently_drop_or_leak() -> None:
    profile = _profile()
    bounds = profile["resource_bounds"]
    observability = profile["observability"]
    assert isinstance(bounds, dict)
    assert isinstance(observability, dict)
    assert all(bounds.values())
    assert observability["node_health_separate_from_verification"] is True
    assert observability["raw_payload_logging"] is False
    assert observability["secret_logging"] is False
    assert observability["collection_gap_state"] is True
    assert observability["clock_quality_state"] is True


def test_gateway_claim_boundary_rejects_unsupported_assurance_claims() -> None:
    profile = _profile()
    claims = profile["claims"]
    assert isinstance(claims, dict)
    assert claims == {
        "truth": False,
        "complete_observation": False,
        "legal_admissibility": False,
        "regulatory_compliance": False,
        "source_system_security": False,
    }


def test_gateway_capacity_numbers_are_unmeasured_non_sla_objectives() -> None:
    profile = _profile()
    objectives = profile["qualification_objectives"]
    assert isinstance(objectives, dict)
    assert objectives["measured"] is False
    assert objectives["sla"] is False
    assert objectives["sustained_events_per_second"] == 1000
    assert objectives["burst_events_per_second"] == 5000
    assert objectives["burst_seconds"] == 600
    assert objectives["max_stream_object_gib"] == 10
    assert objectives["offline_backlog_days"] == 7


def test_gateway_profile_tracks_all_required_g0_documents() -> None:
    profile = _profile()
    documents = profile["required_documents"]
    assert isinstance(documents, list)
    assert set(documents) == REQUIRED_DOCS
    for relative_path in REQUIRED_DOCS:
        assert (ROOT / relative_path).is_file(), relative_path


def test_gateway_schema_has_stable_identity_and_strict_root() -> None:
    schema = _schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "https://lanternprotocol.org/schemas/ets/gateway/v1/profile"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["profile_id"] == {"const": "ets.gateway.reference.pilot.v1"}
    assert schema["properties"]["schema_version"] == {"const": "ets.gateway.profile.v1"}


def test_gateway_requirement_ids_are_unique() -> None:
    profile_text = (ROOT / "docs/spec/ETS_GATEWAY_PROFILE.md").read_text(encoding="utf-8")
    requirement_ids = re.findall(r"GW-G0-\d{3}[A-Z]?", profile_text)
    assert requirement_ids
    assert len(requirement_ids) == len(set(requirement_ids))


def test_gateway_tech_edit_distinguishes_facts_decisions_and_targets() -> None:
    review = (ROOT / "docs/review/ETS_GATEWAY_G0_TECH_EDIT.md").read_text(encoding="utf-8")
    assert "External fact" in review
    assert "ETS design decision" in review
    assert "Qualification objective" in review
    assert "unmeasured, non-SLA qualification objectives" in review
    assert "does not claim full RFC 5425 implementation conformance" in review
