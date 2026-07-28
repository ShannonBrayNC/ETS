# ruff: noqa: E501
"""Scenario engine for the ETS interactive Python testing lab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal

from ets.core import (
    EvidenceEvent,
    EvidenceProofBundle,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    canonical_sha256,
    generate_consistency_proof,
    generate_inclusion_proof,
)
from ets.core.merkle import merkle_root
from ets.core.proofs import InclusionProof, verify_consistency_proof, verify_inclusion_proof
from ets.reports.certificate import create_certificate

JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
LabStatus = Literal["passed", "failed", "informational"]


@dataclass(frozen=True)
class LabComponent:
    """One visible ETS building block in the lab UI."""

    component_id: str
    name: str
    figure: str
    role: str
    demo_capability: str

    def to_public_dict(self) -> dict[str, str]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "figure": self.figure,
            "role": self.role,
            "demo_capability": self.demo_capability,
        }


@dataclass(frozen=True)
class LabScenario:
    """A runnable lab scenario."""

    scenario_id: str
    title: str
    figure_refs: tuple[str, ...]
    capability: str
    expected_result: str

    def to_public_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "figure_refs": list(self.figure_refs),
            "capability": self.capability,
            "expected_result": self.expected_result,
        }


@dataclass(frozen=True)
class LabStep:
    """A narrated test step for UI timelines and CLI summaries."""

    name: str
    status: LabStatus
    detail: str

    def to_public_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class LabRunResult:
    """Structured result for a lab scenario run."""

    scenario_id: str
    title: str
    status: LabStatus
    summary: str
    steps: list[LabStep]
    outputs: dict[str, JsonValue]
    claim_boundary: str

    def to_public_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-native representation for the lab API."""

        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "steps": [step.to_public_dict() for step in self.steps],
            "outputs": self.outputs,
            "claim_boundary": self.claim_boundary,
        }


COMPONENTS: tuple[LabComponent, ...] = (
    LabComponent(
        "source-systems",
        "Source Systems",
        "FIG. 1",
        "Submit AI, GitHub, SignalForge, Christina, OpsHelm, civic, sensor, or human evidence events.",
        "Seed fictional event packets for local proof experiments.",
    ),
    LabComponent(
        "canonicalization",
        "Canonicalization",
        "FIG. 3",
        "Convert hashable event metadata into deterministic canonical JSON.",
        "Show that equivalent JSON payloads hash to the same digest.",
    ),
    LabComponent(
        "event-validator",
        "EvidenceEvent Validator",
        "FIG. 2",
        "Reject malformed event contracts before append.",
        "Exercise strict Pydantic validation for event fields and UTC timestamps.",
    ),
    LabComponent(
        "append-log",
        "Append-Only Log",
        "FIG. 2",
        "Assign monotonic log indexes and compute event and leaf hashes.",
        "Append sample events and inspect indexes, event hashes, and leaf hashes.",
    ),
    LabComponent(
        "merkle-tree",
        "Merkle Tree",
        "FIG. 4",
        "Generate compact inclusion proofs against a tree root.",
        "Build a proof, verify it, and demonstrate tamper failure.",
    ),
    LabComponent(
        "tree-head",
        "Tree-Head Comparison",
        "FIG. 5",
        "Compare tree size and root progression to spot rollback or fork suspicion.",
        "Generate a consistency proof and classify progression.",
    ),
    LabComponent(
        "certificate",
        "Certificate Generator",
        "FIG. 6",
        "Render claim-safe verification certificates from proof bundles.",
        "Produce JSON, Markdown, and HTML certificate previews.",
    ),
    LabComponent(
        "policy-gate",
        "Policy Gate",
        "FIG. 7",
        "Route verified, missing, suspicious, or invalid evidence states.",
        "Map proof outcomes to automation, review, quarantine, or reject decisions.",
    ),
    LabComponent(
        "audit-replay",
        "Audit Replay",
        "FIG. 11",
        "Rebuild verification from event metadata, proofs, tree head, and policy outcome.",
        "Replay a prior event and verify that certificate outputs are reproducible.",
    ),
)

SCENARIOS: tuple[LabScenario, ...] = (
    LabScenario(
        "full-pipeline",
        "Full ETS EvidenceEvent pipeline",
        ("FIG. 1", "FIG. 2", "FIG. 3", "FIG. 4", "FIG. 6", "FIG. 7"),
        "Receive, validate, canonicalize, hash, append, prove, verify, certify, and route.",
        "A proof bundle verifies and routes to human review before external release.",
    ),
    LabScenario(
        "canonical-hash",
        "Canonical hash determinism",
        ("FIG. 3",),
        "Show that equivalent JSON metadata generates a stable canonical SHA-256 digest.",
        "Both payload orderings produce the same canonical digest.",
    ),
    LabScenario(
        "inclusion-proof",
        "Merkle inclusion proof",
        ("FIG. 4",),
        "Generate and verify an inclusion proof for a selected log entry.",
        "The verifier recomputes the path and accepts the proof.",
    ),
    LabScenario(
        "tamper-detection",
        "Tamper detection",
        ("FIG. 4", "FIG. 5"),
        "Mutate proof material and demonstrate root mismatch rejection.",
        "The verifier rejects the altered proof.",
    ),
    LabScenario(
        "policy-routing",
        "Policy-gated routing",
        ("FIG. 7", "FIG. 8", "FIG. 10"),
        "Route evidence states into automation, review, quarantine, reject, archive, or restricted release.",
        "Verified sensitive evidence goes to human review; invalid evidence is quarantined.",
    ),
    LabScenario(
        "civic-boundary",
        "Civic and election-adjacent boundary",
        ("FIG. 9", "FIG. 12"),
        "Demonstrate claim-safe non-claim labels for civic/election-adjacent evidence.",
        "The lab verifies proof material only and repeats the non-voting-software boundary.",
    ),
)

CLAIM_BOUNDARY = (
    "ETS verifies submitted-event metadata, hashes, inclusion proofs, tree-head material, "
    "verification certificates, and policy-routing records. The lab does not prove real-world "
    "truth, legal sufficiency, election correctness, raw evidence authenticity, or completeness "
    "without an external expected-event policy and observation process."
)


def list_components() -> list[dict[str, str]]:
    """Return public component metadata for the UI."""

    return [component.to_public_dict() for component in COMPONENTS]


def list_scenarios() -> list[dict[str, JsonValue]]:
    """Return public scenario metadata for the UI."""

    return [scenario.to_public_dict() for scenario in SCENARIOS]


def run_lab_scenario(scenario_id: str) -> LabRunResult:
    """Run a named lab scenario."""

    if scenario_id == "full-pipeline":
        return _run_full_pipeline()
    if scenario_id == "canonical-hash":
        return _run_canonical_hash()
    if scenario_id == "inclusion-proof":
        return _run_inclusion_proof()
    if scenario_id == "tamper-detection":
        return _run_tamper_detection()
    if scenario_id == "policy-routing":
        return _run_policy_routing()
    if scenario_id == "civic-boundary":
        return _run_civic_boundary()
    raise ValueError(f"unknown lab scenario: {scenario_id}")


def _run_full_pipeline() -> LabRunResult:
    log = _sample_log("full-pipeline", 3)
    entries = log.list_entries()
    entry = entries[-1]
    proof = generate_inclusion_proof(entries, entry.log_index)
    verification = verify_inclusion_proof(proof)
    tree_head = _tree_head_from_proof(proof)
    bundle = EvidenceProofBundle(
        event=entry.event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=tree_head,
        inclusion_proof=proof,
        verification_result=verification,
    )
    certificate = create_certificate(bundle, "markdown")
    routing = _route_policy(verification.valid, sensitive=True, requested_action="external_release")
    return LabRunResult(
        scenario_id="full-pipeline",
        title="Full ETS EvidenceEvent pipeline",
        status="passed" if verification.valid else "failed",
        summary="A fictional event was validated, canonicalized, appended, proven, verified, certified, and policy routed.",
        steps=[
            LabStep("Receive event", "passed", f"Accepted {entry.event.event_id}."),
            LabStep("Canonicalize and hash", "passed", f"Event hash {entry.event_hash[:16]}..."),
            LabStep("Append log", "passed", f"Log index {entry.log_index}; tree size {proof.tree_size}."),
            LabStep("Generate proof", "passed", f"Audit path length {len(proof.audit_path)}."),
            LabStep("Verify proof", "passed" if verification.valid else "failed", verification.reason),
            LabStep("Generate certificate", "passed", "Markdown certificate generated with claim boundaries."),
            LabStep("Policy route", "passed", str(routing["decision"])),
        ],
        outputs={
            "event_id": entry.event.event_id,
            "event_hash": entry.event_hash,
            "leaf_hash": entry.leaf_hash,
            "root_hash": proof.root_hash,
            "tree_size": proof.tree_size,
            "verification": verification.model_dump(mode="json"),
            "routing": routing,
            "certificate_preview": certificate.splitlines()[:14],
        },
        claim_boundary=CLAIM_BOUNDARY,
    )


def _run_canonical_hash() -> LabRunResult:
    payload_a: dict[str, JsonValue] = {
        "event_type": "ai.recommendation",
        "tenant_id": "demo",
        "workspace_id": "lab",
        "metadata": {"risk": "medium", "review_required": True},
    }
    payload_b: dict[str, JsonValue] = {
        "workspace_id": "lab",
        "metadata": {"review_required": True, "risk": "medium"},
        "tenant_id": "demo",
        "event_type": "ai.recommendation",
    }
    digest_a = canonical_sha256(payload_a)
    digest_b = canonical_sha256(payload_b)
    passed = digest_a == digest_b
    return LabRunResult(
        scenario_id="canonical-hash",
        title="Canonical hash determinism",
        status="passed" if passed else "failed",
        summary="Two equivalent JSON payloads with different key orderings were canonicalized and hashed.",
        steps=[
            LabStep("Create payload A", "passed", "Original key order."),
            LabStep("Create payload B", "passed", "Different key order with equivalent values."),
            LabStep("Hash both payloads", "passed" if passed else "failed", "Digests match." if passed else "Digests differ."),
        ],
        outputs={"digest_a": digest_a, "digest_b": digest_b, "match": passed},
        claim_boundary=CLAIM_BOUNDARY,
    )


def _run_inclusion_proof() -> LabRunResult:
    log = _sample_log("inclusion-proof", 4)
    entries = log.list_entries()
    entry = entries[2]
    proof = generate_inclusion_proof(entries, entry.log_index)
    verification = verify_inclusion_proof(proof)
    proof_dump = proof.model_dump(mode="json")
    return LabRunResult(
        scenario_id="inclusion-proof",
        title="Merkle inclusion proof",
        status="passed" if verification.valid else "failed",
        summary="The lab generated an inclusion proof for one entry and verified it against the root hash.",
        steps=[
            LabStep("Append sample events", "passed", f"Created {len(entries)} fictional events."),
            LabStep("Select leaf", "passed", f"Selected index {entry.log_index}."),
            LabStep("Generate proof", "passed", f"Audit path has {len(proof.audit_path)} sibling hashes."),
            LabStep("Verify proof", "passed" if verification.valid else "failed", verification.reason),
        ],
        outputs={
            "selected_event_id": entry.event.event_id,
            "tree_size": proof.tree_size,
            "leaf_index": proof.leaf_index,
            "root_hash": proof.root_hash,
            "audit_path": proof_dump["audit_path"],
            "verification": verification.model_dump(mode="json"),
        },
        claim_boundary=CLAIM_BOUNDARY,
    )


def _run_tamper_detection() -> LabRunResult:
    log = _sample_log("tamper-detection", 3)
    entries = log.list_entries()
    proof = generate_inclusion_proof(entries, 1)
    tampered = proof.model_copy(update={"root_hash": "0" * 64})
    verification = verify_inclusion_proof(tampered)
    passed = not verification.valid
    return LabRunResult(
        scenario_id="tamper-detection",
        title="Tamper detection",
        status="passed" if passed else "failed",
        summary="The lab altered a proof root and verified that ETS rejects the mutated proof material.",
        steps=[
            LabStep("Generate valid proof", "passed", f"Original root {proof.root_hash[:16]}..."),
            LabStep("Mutate root hash", "passed", "Changed the proof root to all zeroes."),
            LabStep("Verify mutated proof", "passed" if passed else "failed", verification.reason),
        ],
        outputs={
            "original_root_hash": proof.root_hash,
            "tampered_root_hash": tampered.root_hash,
            "verification": verification.model_dump(mode="json"),
            "tamper_rejected": passed,
        },
        claim_boundary=CLAIM_BOUNDARY,
    )


def _run_policy_routing() -> LabRunResult:
    verified_sensitive = _route_policy(True, sensitive=True, requested_action="external_release")
    verified_automation = _route_policy(True, sensitive=False, requested_action="trigger_automation")
    invalid = _route_policy(False, sensitive=False, requested_action="trigger_automation")
    return LabRunResult(
        scenario_id="policy-routing",
        title="Policy-gated routing",
        status="passed",
        summary="The lab mapped verified and invalid evidence states to policy outcomes.",
        steps=[
            LabStep("Verified sensitive evidence", "passed", str(verified_sensitive["decision"])),
            LabStep("Verified automation evidence", "passed", str(verified_automation["decision"])),
            LabStep("Invalid proof material", "passed", str(invalid["decision"])),
        ],
        outputs={
            "verified_sensitive": verified_sensitive,
            "verified_automation": verified_automation,
            "invalid": invalid,
        },
        claim_boundary=CLAIM_BOUNDARY,
    )


def _run_civic_boundary() -> LabRunResult:
    log = _sample_log("civic-boundary", 1, event_type="civic.audit_packet")
    entry = log.list_entries()[0]
    proof = generate_inclusion_proof(log.list_entries(), 0)
    verification = verify_inclusion_proof(proof)
    return LabRunResult(
        scenario_id="civic-boundary",
        title="Civic and election-adjacent boundary",
        status="passed" if verification.valid else "failed",
        summary="A fictional civic evidence packet was verified with explicit non-claim labels.",
        steps=[
            LabStep("Create fictional civic packet", "passed", entry.event.event_id),
            LabStep("Generate ETS proof", "passed", f"Tree size {proof.tree_size}."),
            LabStep("Apply non-claim boundary", "passed", "Not voting software, tabulation software, election correctness, or vote of record."),
        ],
        outputs={
            "event_id": entry.event.event_id,
            "proof_valid": verification.valid,
            "non_claim_labels": [
                "not voting software",
                "not tabulation software",
                "not voter registration software",
                "not election correctness software",
                "not vote of record",
            ],
        },
        claim_boundary=CLAIM_BOUNDARY,
    )


def _sample_log(prefix: str, count: int, event_type: str = "workflow.evidence") -> InMemoryAppendOnlyLog:
    log = InMemoryAppendOnlyLog()
    for index in range(count):
        log.append(_sample_event(prefix, index, event_type=event_type))
    return log


def _sample_event(prefix: str, index: int, event_type: str) -> EvidenceEvent:
    content = f"{prefix}:{index}:fictional lab evidence".encode()
    return EvidenceEvent(
        event_id=f"evt-{prefix}-{index}",
        tenant_id="demo-tenant",
        workspace_id="python-lab",
        evidence_id=f"evidence-{prefix}-{index}",
        event_type=event_type,
        subject_ref=f"fictional://ets-lab/{prefix}/{index}",
        content_hash=sha256(content).hexdigest(),
        content_hash_alg="sha256",
        metadata={
            "lab": "ets-python-testing-lab",
            "scenario": prefix,
            "sequence": index,
            "fictional": True,
        },
        created_at_utc=datetime(2026, 6, 14, 12, index, tzinfo=UTC),
        source_system="ets.lab",
        actor_id="lab-runner",
        correlation_id=f"lab-{prefix}",
        external_refs={"figure_refs": ["FIG. 1", "FIG. 2", "FIG. 3"]},
        redaction_profile="none",
    )


def _tree_head_from_proof(proof: InclusionProof) -> SignedTreeHead:
    return SignedTreeHead(
        tree_size=proof.tree_size,
        root_hash=proof.root_hash,
        created_at_utc=datetime.now(UTC),
        log_id="ets-python-lab",
        signature_alg=None,
        signature=None,
        public_key_id=None,
    )


def _route_policy(valid: bool, *, sensitive: bool, requested_action: str) -> dict[str, JsonValue]:
    if not valid:
        return {
            "decision": "Quarantine / Reject",
            "reason": "proof material is invalid or missing",
            "required_state": "Requires Human Review",
        }
    if sensitive or requested_action == "external_release":
        return {
            "decision": "Human Review",
            "reason": "verified proof material is sensitive or externally visible",
            "required_state": "Public Release Restricted",
        }
    if requested_action == "trigger_automation":
        return {
            "decision": "Automation Approval",
            "reason": "proof material verified and no sensitive release flag is present",
            "required_state": "Hash Verified + Inclusion Proof Verified",
        }
    return {
        "decision": "Archive / Restrict Release",
        "reason": "verified evidence is retained for audit replay",
        "required_state": "Archived",
    }


def _tree_root_for_entries(log: InMemoryAppendOnlyLog) -> str:
    return merkle_root([entry.leaf_hash for entry in log.list_entries()])


def run_consistency_progression_demo() -> dict[str, JsonValue]:
    """Return a compact tree-head progression demo for UI and tests."""

    log = _sample_log("tree-head", 4)
    proof = generate_consistency_proof(log.list_entries(), 2)
    verification = verify_consistency_proof(proof)
    return {
        "previous_tree_size": proof.previous_tree_size,
        "latest_tree_size": proof.latest_tree_size,
        "previous_root_hash": proof.previous_root_hash,
        "latest_root_hash": proof.latest_root_hash,
        "computed_latest_root": _tree_root_for_entries(log),
        "verification": verification.model_dump(mode="json"),
    }
