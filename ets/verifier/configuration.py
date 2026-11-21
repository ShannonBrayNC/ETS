"""Bounded verification for exported configuration-assurance verdict packages."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ets.core import EvidenceProofBundle
from ets.verifier.service import (
    TreeHeadTrustStore,
    VerifierOutcome,
    VerifierPolicy,
    verify_offline_bundle,
)

_SHA256_PATTERN = r"^[0-9a-f]{64}$"

ArtifactRole = Literal["baseline", "before_state", "approval", "tool_result", "read_back"]
ConfigurationVerdict = Literal["compliant", "drifted", "repaired", "repair_failed", "unknown"]
AuthorizationAssessment = Literal["authorized", "unauthorized", "unknown", "not_applicable"]
RepairAssessment = Literal["not_attempted", "verified", "failed", "unknown"]
IntegrityStatus = Literal["valid", "invalid"]
TrustStatus = Literal["trusted", "untrusted"]
UncertaintyStatus = Literal["none_declared", "declared", "verification_failure"]

_REQUIRED_ROLES: frozenset[str] = frozenset(
    {"baseline", "before_state", "approval", "tool_result", "read_back"}
)


class StrictConfigurationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class ConfigurationArtifactBindingV1(StrictConfigurationModel):
    """Digest and size binding for one separately exported artifact."""

    role: ArtifactRole
    artifact_id: str = Field(min_length=1, max_length=256)
    media_type: str = Field(min_length=1, max_length=256)
    sha256: str = Field(pattern=_SHA256_PATTERN)
    byte_length: int = Field(ge=0, le=16 * 1024 * 1024)


class ConfigurationVerdictV1(StrictConfigurationModel):
    """One bounded configuration verdict; it is a claim, not its own proof."""

    schema_version: Literal["ets.configuration_verdict.v1"] = "ets.configuration_verdict.v1"
    verdict_id: str = Field(min_length=1, max_length=256)
    case_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=512)
    baseline_id: str = Field(min_length=1, max_length=256)
    verdict: ConfigurationVerdict
    authorization: AuthorizationAssessment
    repair: RepairAssessment
    uncertainties: tuple[str, ...] = ()
    artifacts: tuple[ConfigurationArtifactBindingV1, ...]

    @model_validator(mode="after")
    def validate_verdict_contract(self) -> Self:
        roles = [artifact.role for artifact in self.artifacts]
        if len(roles) != len(set(roles)):
            raise ValueError("configuration verdict cannot contain duplicate artifact roles")
        if set(roles) != _REQUIRED_ROLES:
            raise ValueError("configuration verdict requires exactly the five artifact roles")
        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("configuration verdict artifact_id values must be unique")
        if any(not item.strip() for item in self.uncertainties):
            raise ValueError("configuration verdict uncertainties cannot be blank")
        if len(self.uncertainties) != len(set(self.uncertainties)):
            raise ValueError("configuration verdict uncertainties cannot be duplicated")

        if self.verdict == "repaired":
            if self.authorization != "authorized" or self.repair != "verified":
                raise ValueError("a repaired verdict requires authorized and verified assessments")
            if self.uncertainties:
                raise ValueError("a repaired verdict cannot suppress declared uncertainty")
        elif self.verdict == "repair_failed":
            if self.repair != "failed":
                raise ValueError("a repair_failed verdict requires a failed repair assessment")
        elif self.verdict == "unknown":
            if not self.uncertainties:
                raise ValueError("an unknown verdict requires an uncertainty statement")
        elif self.repair != "not_attempted":
            raise ValueError("compliant and drifted verdicts require repair=not_attempted")
        return self


class ConfigurationVerificationCheck(StrictConfigurationModel):
    code: str = Field(min_length=1, max_length=128)
    passed: bool
    reason: str = Field(min_length=1, max_length=2048)


class ConfigurationVerdictVerificationV1(StrictConfigurationModel):
    """Fresh verifier result with independent claim dimensions."""

    schema_version: Literal["ets.configuration_verdict_verification.v1"] = (
        "ets.configuration_verdict_verification.v1"
    )
    valid: bool
    verdict_id: str
    case_id: str
    target_id: str
    baseline_id: str
    verdict: ConfigurationVerdict
    integrity: IntegrityStatus
    trust: TrustStatus
    authorization: AuthorizationAssessment
    repair: RepairAssessment
    uncertainty: UncertaintyStatus
    uncertainties: tuple[str, ...]
    checks: tuple[ConfigurationVerificationCheck, ...]
    proof: VerifierOutcome
    claim_boundary: Literal[
        "bounded_configuration_package_integrity_and_checkpoint_trust_not_source_truth_authority_or_real_world_repair_proof"
    ] = (
        "bounded_configuration_package_integrity_and_checkpoint_trust_not_source_truth_authority_or_real_world_repair_proof"
    )


def verify_configuration_verdict_package(
    *,
    verdict_bytes: bytes,
    proof_bundle: EvidenceProofBundle | Mapping[str, Any],
    artifact_payloads: Mapping[str, bytes],
    trust_store: TreeHeadTrustStore,
    policy: VerifierPolicy,
) -> ConfigurationVerdictVerificationV1:
    """Verify exported bytes and their existing ETS checkpoint proof.

    Authorization and repair are reported as signed verdict claims. Digest and proof checks do not
    independently establish that the approver had authority or that the target actually changed.
    """

    verdict = _parse_verdict(verdict_bytes)
    bundle = (
        proof_bundle
        if isinstance(proof_bundle, EvidenceProofBundle)
        else EvidenceProofBundle.model_validate(proof_bundle)
    )
    proof = verify_offline_bundle(bundle, trust_store=trust_store, policy=policy)
    checks: list[ConfigurationVerificationCheck] = []

    payload_digest = hashlib.sha256(verdict_bytes).hexdigest()
    _check(
        checks,
        "verdict_payload_hash",
        payload_digest == bundle.event.content_hash,
        "exported verdict bytes match the ETS event content hash",
        "exported verdict bytes do not match the ETS event content hash",
    )
    event_bound = (
        bundle.event.event_type == "configuration.verdict"
        and bundle.event.evidence_id == verdict.verdict_id
        and bundle.event.correlation_id == verdict.case_id
        and bundle.event.subject_ref == f"configuration-target:{verdict.target_id}"
        and bundle.event.metadata.get("baseline_id") == verdict.baseline_id
    )
    _check(
        checks,
        "verdict_event_binding",
        event_bound,
        "ETS event binds the verdict, case, target, and baseline",
        "ETS event does not bind the verdict, case, target, and baseline",
    )

    expected_ids = {artifact.artifact_id for artifact in verdict.artifacts}
    unexpected_ids = set(artifact_payloads) - expected_ids
    _check(
        checks,
        "artifact_set",
        not unexpected_ids,
        "no undeclared artifact payloads were supplied",
        "undeclared artifact payloads were supplied",
    )
    for artifact in verdict.artifacts:
        raw = artifact_payloads.get(artifact.artifact_id)
        present = raw is not None
        _check(
            checks,
            f"artifact_presence:{artifact.role}",
            present,
            f"{artifact.role} artifact bytes are present",
            f"{artifact.role} artifact bytes are missing",
        )
        if raw is None:
            continue
        matches = (
            len(raw) == artifact.byte_length
            and hashlib.sha256(raw).hexdigest() == artifact.sha256
        )
        _check(
            checks,
            f"artifact_digest:{artifact.role}",
            matches,
            f"{artifact.role} artifact bytes match size and SHA-256",
            f"{artifact.role} artifact bytes do not match size and SHA-256",
        )

    proof_integrity = all(
        item.passed for item in proof.checks if item.code != "tree_head_signature"
    )
    _check(
        checks,
        "ets_proof_integrity",
        proof_integrity,
        "ETS event, leaf, inclusion proof, and checkpoint bindings verify",
        "ETS proof integrity or checkpoint binding failed",
    )
    _check(
        checks,
        "ets_checkpoint_trust",
        proof.signature_verified,
        "checkpoint signature verifies against the supplied trust store",
        "checkpoint signature does not verify against the supplied trust store",
    )

    integrity: IntegrityStatus = "valid" if all(
        item.passed for item in checks if item.code != "ets_checkpoint_trust"
    ) else "invalid"
    trust: TrustStatus = "trusted" if proof.signature_verified else "untrusted"
    if integrity == "invalid" or trust == "untrusted":
        uncertainty: UncertaintyStatus = "verification_failure"
    elif verdict.uncertainties:
        uncertainty = "declared"
    else:
        uncertainty = "none_declared"

    return ConfigurationVerdictVerificationV1(
        valid=integrity == "valid" and trust == "trusted",
        verdict_id=verdict.verdict_id,
        case_id=verdict.case_id,
        target_id=verdict.target_id,
        baseline_id=verdict.baseline_id,
        verdict=verdict.verdict,
        integrity=integrity,
        trust=trust,
        authorization=verdict.authorization,
        repair=verdict.repair,
        uncertainty=uncertainty,
        uncertainties=verdict.uncertainties,
        checks=tuple(checks),
        proof=proof,
    )


def _parse_verdict(raw: bytes) -> ConfigurationVerdictV1:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    payload = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=reject_duplicates)
    if isinstance(payload, dict):
        if isinstance(payload.get("uncertainties"), list):
            payload["uncertainties"] = tuple(payload["uncertainties"])
        if isinstance(payload.get("artifacts"), list):
            payload["artifacts"] = tuple(payload["artifacts"])
    return ConfigurationVerdictV1.model_validate(payload)


def _check(
    checks: list[ConfigurationVerificationCheck],
    code: str,
    passed: bool,
    pass_reason: str,
    fail_reason: str,
) -> None:
    checks.append(
        ConfigurationVerificationCheck(
            code=code,
            passed=passed,
            reason=pass_reason if passed else fail_reason,
        )
    )


__all__ = [
    "ConfigurationArtifactBindingV1",
    "ConfigurationVerdictV1",
    "ConfigurationVerdictVerificationV1",
    "verify_configuration_verdict_package",
]
