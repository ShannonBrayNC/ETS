from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAPTURE_PATH = ROOT / "scripts" / "qualification" / "legacy_lab" / "capture_udp_syslog.py"
HARNESS_PATH = ROOT / "scripts" / "qualification" / "legacy_lab" / "characterize_router.py"


def _load_capture_module():
    spec = importlib.util.spec_from_file_location("capture_udp_syslog", CAPTURE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_syslog_classifier_detects_rfc5424_after_exact_byte_boundary() -> None:
    module = _load_capture_module()
    payload = b"<34>1 2026-09-18T04:00:00Z router labapp 123 ID47 - synthetic"
    classification, observations = module.classify(payload)

    assert classification == "rfc5424_version_1_candidate"
    assert observations["hostname_observation"] == "router"
    assert observations["app_name_observation"] == "labapp"
    assert observations["identity_boundary"].endswith("not_authenticated_identity")


def test_syslog_classifier_detects_rfc3164_like() -> None:
    module = _load_capture_module()
    classification, observations = module.classify(
        b"<34>Sep 18 04:00:00 router synthetic test"
    )

    assert classification == "rfc3164_like_candidate"
    assert observations["identity_boundary"].endswith("not_authenticated_identity")


def test_syslog_classifier_preserves_vendor_specific_boundary() -> None:
    module = _load_capture_module()
    classification, observations = module.classify(b"vendor-specific synthetic message")

    assert classification == "vendor_specific_or_unclassified"
    assert observations["identity_boundary"].endswith("not_authenticated_identity")


def test_characterization_harness_preserves_safety_and_claim_boundaries() -> None:
    text = HARNESS_PATH.read_text(encoding="utf-8")

    assert "active default route" in text
    assert "qualification_claim" in text
    assert "authenticated_source_identity_claim" in text
    assert "characterization_only_not_hardware_qualification" in text
    assert "rfc5424_profile_candidate" in text
    assert "bounded_adapter_or_fault_infrastructure_candidate" in text
    assert "no_remote_syslog_observed" in text


def test_lab_nic_preparation_is_plan_gated_and_preserves_management_route() -> None:
    text = LAB_NIC_PATH.read_text(encoding="utf-8")

    assert '"--apply"' in text
    assert "PLAN ONLY: no network configuration was changed." in text
    assert "alternate_default_route_interfaces" in text
    assert "no other interface currently provides a default route" in text
    assert '"ipv4.never-default"' in text
    assert '"yes"' in text
    assert "LAB_NIC_READY=true" in text
    assert "Rollback:" in text
    assert "lab_network_preparation_only_not_hardware_qualification" in text


def test_lab_nic_preparation_has_valid_python_syntax() -> None:
    source = LAB_NIC_PATH.read_text(encoding="utf-8")
    compile(source, str(LAB_NIC_PATH), "exec")
