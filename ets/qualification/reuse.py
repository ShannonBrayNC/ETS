"""Cross-product HQP reuse contract for Android and legacy hardware profiles."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.qualification.profile import HardwareQualificationProfile

_SHA_RE = r"^[0-9a-f]{40,64}$"
_REQUIRED_EVIDENCE_CLASSES = {
    "dut_identity",
    "environment",
    "build_identity",
    "observer_identity",
    "starting_state",
    "stimulus",
    "observations",
    "resulting_state",
    "verifier_output",
    "qualification_report",
}
_REQUIRED_VERIFIER_CHECKS = {
    "schema_conformance",
    "artifact_presence",
    "digest_validity",
    "signature_validity",
    "evidence_object_binding",
    "test_case_completion",
    "observation_result_linkage",
    "deviation_policy",
    "disposition_policy",
}
_CLAIM_BOUNDARY: Literal[
    "cross_product_hqp_reuse_not_physical_qualification_truth_completeness_compliance_or_safety_proof"
] = "cross_product_hqp_reuse_not_physical_qualification_truth_completeness_compliance_or_safety_proof"


class StrictReuseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class SourceContract(StrictReuseModel):
    repository: str = Field(min_length=3, max_length=512)
    path: str = Field(min_length=1, max_length=1024)
    commit_sha: str = Field(pattern=_SHA_RE)
    issue_refs: tuple[str, ...] = Field(min_length=1)


class ReuseBinding(StrictReuseModel):
    source_field: str = Field(min_length=1, max_length=256)
    hqp_target: str = Field(min_length=1, max_length=512)
    evidence_role: str = Field(min_length=1, max_length=256)
    required: bool = True
    notes: str | None = Field(default=None, max_length=2048)


class CrossProductReuseManifest(StrictReuseModel):
    schema_version: Literal["ets.hqp-cross-product-reuse.v1"]
    reuse_id: str = Field(min_length=3, max_length=256)
    product_name: str = Field(min_length=1, max_length=256)
    target_class_id: str = Field(min_length=1, max_length=128)
    profile_id: str = Field(min_length=3, max_length=256)
    profile_version: str = Field(min_length=1, max_length=128)
    source_contract: SourceContract
    bindings: tuple[ReuseBinding, ...] = Field(min_length=1)
    product_specific_extensions: tuple[str, ...] = ()
    physical_exit_gate: str = Field(min_length=1, max_length=4096)
    claim_boundary: Literal[
        "cross_product_hqp_reuse_not_physical_qualification_truth_completeness_compliance_or_safety_proof"
    ] = _CLAIM_BOUNDARY

    @model_validator(mode="after")
    def require_unique_bindings(self) -> CrossProductReuseManifest:
        source_fields = tuple(item.source_field for item in self.bindings)
        if len(source_fields) != len(set(source_fields)):
            raise ValueError("reuse binding source_field values must be unique")
        return self


def load_reuse_manifest(raw: bytes) -> CrossProductReuseManifest:
    return CrossProductReuseManifest.model_validate_json(raw)


def validate_reuse_profile(
    profile: HardwareQualificationProfile,
    manifest: CrossProductReuseManifest,
) -> None:
    """Reject product profiles that weaken the common HQP portability contract."""

    if profile.base_profile != "ets.hardware-qualification.v1":
        raise ValueError("reuse profile must inherit ets.hardware-qualification.v1")
    if profile.profile_id != manifest.profile_id:
        raise ValueError("manifest profile_id does not match profile")
    if profile.profile_version != manifest.profile_version:
        raise ValueError("manifest profile_version does not match profile")

    evidence_classes = {item.value for item in profile.evidence_requirements.required_classes}
    if evidence_classes != _REQUIRED_EVIDENCE_CLASSES:
        raise ValueError("reuse profile must retain the full common HQP evidence-class set")
    if not profile.evidence_requirements.evidence_object_binding_required:
        raise ValueError("reuse profile cannot disable Evidence Object binding")
    if not profile.evidence_requirements.raw_artifact_digest_required:
        raise ValueError("reuse profile cannot disable raw artifact digests")

    verifier_checks = {item.value for item in profile.verifier_requirements.checks}
    if verifier_checks != _REQUIRED_VERIFIER_CHECKS:
        raise ValueError("reuse profile must retain the full common HQP verifier-check set")
    required_independent = set(profile.verifier_requirements.independent_verification_required_for)
    if required_independent != {"qualified", "qualified_with_deviation"}:
        raise ValueError("reuse profile must require independent verification for qualified claims")
    if profile.verifier_requirements.dut_runtime_may_be_trusted:
        raise ValueError("reuse profile cannot trust the DUT runtime")

    case_ids = {item.test_id for item in profile.test_cases}
    if not case_ids:
        raise ValueError("reuse profile must define product-specific executable cases")

    required_bindings = {item.source_field for item in manifest.bindings if item.required}
    if not required_bindings:
        raise ValueError("reuse manifest must bind at least one required source field")


def common_hqp_semantics_fingerprint(profile: HardwareQualificationProfile) -> str:
    """Fingerprint only the common semantics that must remain portable across products."""

    payload = {
        "base_profile": profile.base_profile,
        "evidence_requirements": profile.evidence_requirements.model_dump(mode="json"),
        "verifier_requirements": profile.verifier_requirements.model_dump(mode="json"),
        "disposition_policy": profile.disposition_policy.model_dump(mode="json"),
        "capability_states_are_independent": (
            profile.capability_boundary.capability_states_are_independent
        ),
        "cross_revision_qualification_allowed": (
            profile.device_constraints.cross_revision_qualification_allowed
        ),
        "requalify_on_claim_critical_change": (
            profile.validity_policy.requalify_on_claim_critical_change
        ),
        "supersession_must_be_explicit": profile.validity_policy.supersession_must_be_explicit,
        "historical_results_immutable": profile.validity_policy.historical_results_immutable,
    }
    return canonical_sha256(payload)


def render_reuse_summary(
    profile: HardwareQualificationProfile,
    manifest: CrossProductReuseManifest,
) -> str:
    validate_reuse_profile(profile, manifest)
    payload = {
        "reuse_id": manifest.reuse_id,
        "product_name": manifest.product_name,
        "target_class_id": manifest.target_class_id,
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "common_semantics_fingerprint": common_hqp_semantics_fingerprint(profile),
        "source_contract": manifest.source_contract.model_dump(mode="json"),
        "physical_exit_gate": manifest.physical_exit_gate,
        "claim_boundary": manifest.claim_boundary,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = [
    "CrossProductReuseManifest",
    "ReuseBinding",
    "SourceContract",
    "common_hqp_semantics_fingerprint",
    "load_reuse_manifest",
    "render_reuse_summary",
    "validate_reuse_profile",
]
