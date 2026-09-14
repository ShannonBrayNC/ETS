from __future__ import annotations

from pathlib import Path

import pytest

from ets.qualification.profile import HardwareQualificationProfile
from ets.qualification.reuse import (
    common_hqp_semantics_fingerprint,
    load_reuse_manifest,
    render_reuse_summary,
    validate_reuse_profile,
)

_ROOT = Path(__file__).parents[2]
_ANDROID_PROFILE_PATH = (
    _ROOT
    / "docs"
    / "qualification"
    / "profiles"
    / "ets-provenance-android-phase1a-hardware-qualification-v1.json"
)
_ANDROID_MANIFEST_PATH = (
    _ROOT
    / "docs"
    / "qualification"
    / "reuse"
    / "android-phase1a-hqp-reuse-v1.json"
)
_LEGACY_PROFILE_PATH = (
    _ROOT
    / "docs"
    / "qualification"
    / "profiles"
    / "ets-legacy-network-syslog-hardware-qualification-v1.json"
)
_LEGACY_MANIFEST_PATH = (
    _ROOT
    / "docs"
    / "qualification"
    / "reuse"
    / "legacy-network-syslog-hqp-reuse-v1.json"
)


def _load_profile(path: Path) -> HardwareQualificationProfile:
    return HardwareQualificationProfile.model_validate_json(path.read_bytes())


def test_android_and_legacy_reuse_profiles_validate() -> None:
    android_profile = _load_profile(_ANDROID_PROFILE_PATH)
    android_manifest = load_reuse_manifest(_ANDROID_MANIFEST_PATH.read_bytes())
    legacy_profile = _load_profile(_LEGACY_PROFILE_PATH)
    legacy_manifest = load_reuse_manifest(_LEGACY_MANIFEST_PATH.read_bytes())

    validate_reuse_profile(android_profile, android_manifest)
    validate_reuse_profile(legacy_profile, legacy_manifest)

    assert android_manifest.target_class_id == "ANDROID-PHASE1A-RT0"
    assert legacy_manifest.target_class_id == "LEGACY-NET-SYSLOG-RT0"


def test_products_share_identical_common_hqp_semantics() -> None:
    android_profile = _load_profile(_ANDROID_PROFILE_PATH)
    legacy_profile = _load_profile(_LEGACY_PROFILE_PATH)

    android_fingerprint = common_hqp_semantics_fingerprint(android_profile)
    legacy_fingerprint = common_hqp_semantics_fingerprint(legacy_profile)

    assert len(android_fingerprint) == 64
    assert android_fingerprint == legacy_fingerprint


def test_android_reuse_is_pinned_to_current_phase1a_contract() -> None:
    manifest = load_reuse_manifest(_ANDROID_MANIFEST_PATH.read_bytes())

    assert manifest.source_contract.repository == "Lantern-Protocol/ETS-Mobile"
    assert manifest.source_contract.path == "docs/ANDROID_PHASE1A_DEVICE_QUALIFICATION.md"
    assert manifest.source_contract.commit_sha == "fefba5069da1d33251211dd3d67d176bade478c2"
    assert "Lantern-Protocol/ETS-Mobile#4" in manifest.source_contract.issue_refs


def test_legacy_reuse_preserves_udp_identity_nonclaim() -> None:
    profile = _load_profile(_LEGACY_PROFILE_PATH)
    manifest = load_reuse_manifest(_LEGACY_MANIFEST_PATH.read_bytes())

    assert "authenticated_udp_source_identity" in profile.non_claims
    source_binding = next(
        item for item in manifest.bindings if item.source_field == "source_ip_port_observation"
    )
    assert source_binding.notes is not None
    assert "never authenticated device identity" in source_binding.notes


def test_reuse_profile_cannot_drop_common_verifier_check() -> None:
    profile = _load_profile(_ANDROID_PROFILE_PATH)
    manifest = load_reuse_manifest(_ANDROID_MANIFEST_PATH.read_bytes())
    weakened_verifier = profile.verifier_requirements.model_copy(
        update={
            "checks": tuple(
                item
                for item in profile.verifier_requirements.checks
                if item.value != "evidence_object_binding"
            )
        }
    )
    weakened_profile = profile.model_copy(update={"verifier_requirements": weakened_verifier})

    with pytest.raises(ValueError, match="full common HQP verifier-check set"):
        validate_reuse_profile(weakened_profile, manifest)


def test_reuse_profile_cannot_drop_common_evidence_class() -> None:
    profile = _load_profile(_LEGACY_PROFILE_PATH)
    manifest = load_reuse_manifest(_LEGACY_MANIFEST_PATH.read_bytes())
    weakened_evidence = profile.evidence_requirements.model_copy(
        update={
            "required_classes": tuple(
                item
                for item in profile.evidence_requirements.required_classes
                if item.value != "resulting_state"
            )
        }
    )
    weakened_profile = profile.model_copy(update={"evidence_requirements": weakened_evidence})

    with pytest.raises(ValueError, match="full common HQP evidence-class set"):
        validate_reuse_profile(weakened_profile, manifest)


def test_reuse_summary_is_deterministic_and_keeps_physical_gate() -> None:
    profile = _load_profile(_ANDROID_PROFILE_PATH)
    manifest = load_reuse_manifest(_ANDROID_MANIFEST_PATH.read_bytes())

    first = render_reuse_summary(profile, manifest)
    second = render_reuse_summary(profile, manifest)

    assert first == second
    assert "common_semantics_fingerprint" in first
    assert "Repository CI alone does not satisfy this gate" in first
