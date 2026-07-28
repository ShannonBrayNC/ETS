# ETS Policy-Gated Routing Guide

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: architects, workflow engineers, security reviewers, governance owners, and automation builders

## 1. Purpose

ETS policy-gated routing turns a verification result into a controlled action. A valid proof should not automatically trigger every downstream workflow. ETS should route evidence based on proof state, event type, sensitivity, tenant/workspace scope, external-release intent, civic/election-adjacent classification, and deployment owner policy.

This guide defines the decision model and gives Python examples for implementing routing in local ETS integrations.

## 2. Claim boundary

ETS routing verifies and routes submitted-event metadata, hashes, inclusion proofs, tree-head material, verification certificates, and policy-routing records.

ETS does not prove real-world truth, legal sufficiency, official chain of custody, election correctness, vote totals, ballot validity, raw evidence authenticity, or completeness without an external expected-event policy and observation process.

All examples are fictional, local-only, and non-PII.

## 3. Decision vocabulary

Use a small, stable vocabulary so downstream systems do not invent unsafe meanings.

| Decision | Meaning | Typical next action |
|---|---|---|
| `Automation Approval` | Proof material is valid and policy allows automation. | Continue workflow, create ticket, approve release gate, update low-risk record. |
| `Human Review` | Proof is valid, but sensitivity or policy requires review. | Assign reviewer, require sign-off, delay publication. |
| `Quarantine / Reject` | Proof is invalid, missing, mismatched, stale, or untrusted. | Block action, preserve packet, notify owner. |
| `Archive / Restrict Release` | Evidence is valid but should be retained or restricted. | Archive for replay, hide public details. |
| `Public Release Restricted` | Evidence touches public/civic/regulated/reputational surface. | Require release authority review. |

## 4. Evidence states

ETS routing should consume evidence states, not raw trust adjectives.

```text
Submitted
Schema Validated
Canonicalized
Content Hash Present
Event Hash Computed
Appended
Inclusion Proof Generated
Inclusion Proof Verified
Tree Head Accepted
Consistency Verified
Certificate Generated
Policy Routed
Requires Human Review
Public Release Restricted
Quarantined
Rejected
Archived
```

## 5. Routing inputs

A routing call should receive a structured request:

```json
{
  "event_id": "evt-demo-001",
  "event_type": "ai.output.generated",
  "tenant_id": "demo-tenant",
  "workspace_id": "demo-workspace",
  "proof_valid": true,
  "tree_head_accepted": true,
  "consistency_verified": true,
  "requested_action": "external_release",
  "sensitivity": "regulated",
  "external_release": true,
  "civic_or_election_adjacent": false,
  "source_system": "ai-agent-demo",
  "policy_version": "ets-routing-policy-v1"
}
```

## 6. Policy ordering

Evaluate hard-stop conditions first. Then evaluate restricted classifications. Then allow automation only if no earlier gate blocked it.

```text
1. Invalid or missing proof -> Quarantine / Reject
2. Unaccepted tree head -> Quarantine / Reject
3. Consistency failure -> Quarantine / Reject
4. Civic/election-adjacent evidence -> Human Review + Public Release Restricted
5. Regulated or restricted sensitivity -> Human Review
6. External release -> Human Review
7. Approved low-risk automation action -> Automation Approval
8. Default -> Archive / Restrict Release
```

## 7. Python routing model

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Decision = Literal[
    "Automation Approval",
    "Human Review",
    "Quarantine / Reject",
    "Archive / Restrict Release",
]

Sensitivity = Literal["public", "internal", "confidential", "restricted", "regulated"]


@dataclass(frozen=True)
class RoutingRequest:
    event_id: str
    event_type: str
    tenant_id: str
    workspace_id: str
    proof_valid: bool
    tree_head_accepted: bool
    consistency_verified: bool
    requested_action: str
    sensitivity: Sensitivity
    external_release: bool
    civic_or_election_adjacent: bool
    source_system: str
    policy_version: str = "ets-routing-policy-v1"
    evidence_states: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RoutingDecision:
    decision: Decision
    required_state: str
    reason: str
    policy_version: str
    reviewer_role: str | None = None
    public_release_allowed: bool = False
    automation_allowed: bool = False


def route_ets_evidence(request: RoutingRequest) -> RoutingDecision:
    if not request.proof_valid:
        return RoutingDecision(
            decision="Quarantine / Reject",
            required_state="Requires Human Review",
            reason="proof material is invalid, missing, or root-mismatched",
            policy_version=request.policy_version,
            reviewer_role="evidence-owner",
        )

    if not request.tree_head_accepted:
        return RoutingDecision(
            decision="Quarantine / Reject",
            required_state="Tree Head Review Required",
            reason="tree head was not accepted by the verifier",
            policy_version=request.policy_version,
            reviewer_role="security-reviewer",
        )

    if not request.consistency_verified:
        return RoutingDecision(
            decision="Quarantine / Reject",
            required_state="Consistency Review Required",
            reason="tree-head progression is not verified",
            policy_version=request.policy_version,
            reviewer_role="security-reviewer",
        )

    if request.civic_or_election_adjacent:
        return RoutingDecision(
            decision="Human Review",
            required_state="Public Release Restricted",
            reason="civic/election-adjacent evidence requires explicit non-claim review",
            policy_version=request.policy_version,
            reviewer_role="civic-boundary-reviewer",
        )

    if request.sensitivity in {"confidential", "restricted", "regulated"}:
        return RoutingDecision(
            decision="Human Review",
            required_state="Public Release Restricted",
            reason="verified proof material is sensitive or regulated",
            policy_version=request.policy_version,
            reviewer_role="data-owner",
        )

    if request.external_release:
        return RoutingDecision(
            decision="Human Review",
            required_state="Public Release Restricted",
            reason="external publication requires release review even when proof is valid",
            policy_version=request.policy_version,
            reviewer_role="release-owner",
        )

    if request.requested_action in {"trigger_automation", "create_ticket", "approve_release"}:
        return RoutingDecision(
            decision="Automation Approval",
            required_state="Hash Verified + Inclusion Proof Verified",
            reason="proof material verified and no sensitive release flag is present",
            policy_version=request.policy_version,
            automation_allowed=True,
        )

    return RoutingDecision(
        decision="Archive / Restrict Release",
        required_state="Archived",
        reason="verified evidence retained for audit replay",
        policy_version=request.policy_version,
    )
```

## 8. Attach routing to an ETS proof bundle

```python
from ets.core.proofs import verify_inclusion_proof


def route_bundle(bundle: dict[str, object]) -> RoutingDecision:
    proof = bundle["inclusion_proof"]
    verification = verify_inclusion_proof(proof)  # use model object in real code
    event = bundle["event"]
    metadata = dict(event.get("metadata", {}))

    request = RoutingRequest(
        event_id=str(event["event_id"]),
        event_type=str(event["event_type"]),
        tenant_id=str(event["tenant_id"]),
        workspace_id=str(event["workspace_id"]),
        proof_valid=bool(verification.valid),
        tree_head_accepted=True,
        consistency_verified=True,
        requested_action=str(metadata.get("requested_action", "archive")),
        sensitivity=str(metadata.get("sensitivity", "internal")),
        external_release=bool(metadata.get("external_release", False)),
        civic_or_election_adjacent=bool(metadata.get("civic_or_election_adjacent", False)),
        source_system=str(event.get("source_system", "unknown")),
    )
    return route_ets_evidence(request)
```

## 9. Routing examples

```python
valid_low_risk = RoutingRequest(
    event_id="evt-low-risk-001",
    event_type="workflow.evidence",
    tenant_id="demo",
    workspace_id="routing",
    proof_valid=True,
    tree_head_accepted=True,
    consistency_verified=True,
    requested_action="create_ticket",
    sensitivity="internal",
    external_release=False,
    civic_or_election_adjacent=False,
    source_system="opshelm-demo",
)
assert route_ets_evidence(valid_low_risk).decision == "Automation Approval"

invalid = valid_low_risk.__class__(**{**valid_low_risk.__dict__, "proof_valid": False})
assert route_ets_evidence(invalid).decision == "Quarantine / Reject"

civic = valid_low_risk.__class__(**{**valid_low_risk.__dict__, "civic_or_election_adjacent": True})
assert route_ets_evidence(civic).decision == "Human Review"
```

## 10. Persist a routing event

After routing, record the decision as its own ETS event so the action is replayable.

```python
from datetime import UTC, datetime
from hashlib import sha256

from ets.core import EvidenceEvent


def build_routing_event(original_event_id: str, decision: RoutingDecision) -> EvidenceEvent:
    decision_bytes = str(decision).encode("utf-8")
    return EvidenceEvent(
        event_id=f"evt-route-{original_event_id}",
        tenant_id="demo-tenant",
        workspace_id="routing",
        evidence_id=f"routing-{original_event_id}",
        event_type="ets.policy.route",
        subject_ref=f"fictional://routing/{original_event_id}",
        content_hash=sha256(decision_bytes).hexdigest(),
        content_hash_alg="sha256",
        metadata={
            "original_event_id": original_event_id,
            "decision": decision.decision,
            "required_state": decision.required_state,
            "reason": decision.reason,
            "policy_version": decision.policy_version,
            "reviewer_role": decision.reviewer_role,
            "automation_allowed": decision.automation_allowed,
            "public_release_allowed": decision.public_release_allowed,
        },
        created_at_utc=datetime.now(UTC),
        source_system="ets-policy-gate",
        actor_id="policy-engine",
        correlation_id=f"route-{original_event_id}",
        external_refs={"original_event_id": original_event_id},
        redaction_profile="none",
    )
```

## 11. Tests

```python
def test_invalid_proof_is_quarantined() -> None:
    request = RoutingRequest(
        event_id="evt-1",
        event_type="workflow.evidence",
        tenant_id="demo",
        workspace_id="test",
        proof_valid=False,
        tree_head_accepted=True,
        consistency_verified=True,
        requested_action="trigger_automation",
        sensitivity="internal",
        external_release=False,
        civic_or_election_adjacent=False,
        source_system="unit-test",
    )
    decision = route_ets_evidence(request)
    assert decision.decision == "Quarantine / Reject"
    assert decision.automation_allowed is False


def test_external_release_requires_human_review() -> None:
    request = RoutingRequest(
        event_id="evt-2",
        event_type="report.publication",
        tenant_id="demo",
        workspace_id="test",
        proof_valid=True,
        tree_head_accepted=True,
        consistency_verified=True,
        requested_action="external_release",
        sensitivity="public",
        external_release=True,
        civic_or_election_adjacent=False,
        source_system="unit-test",
    )
    assert route_ets_evidence(request).decision == "Human Review"
```

## 12. Operator checklist

```text
[ ] Routing consumes verification outputs, not source-system trust labels.
[ ] Invalid, missing, stale, or mismatched proof cannot trigger automation.
[ ] Civic/election-adjacent packets always require explicit human review.
[ ] Regulated or external-release events default to human review.
[ ] Automation Approval is narrow and logged as its own ETS event.
[ ] Routing decisions include policy version and reason.
[ ] Certificates show routing result and non-claim boundary.
[ ] Tests cover invalid proof, external release, civic packets, and low-risk automation.
```

## 13. References

- ETS Developer Quickstart: `docs/implementation/ETS_DEVELOPER_QUICKSTART.md`
- ETS Security Hardening Guide: `docs/implementation/ETS_SECURITY_HARDENING_GUIDE.md`
- ETS Certificate and Public Verifier Guide: `docs/implementation/ETS_CERTIFICATE_PUBLIC_VERIFIER_GUIDE.md`
