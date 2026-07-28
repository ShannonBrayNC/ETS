# ETS AI Governance and Agent Accountability Guide

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: AI architects, governance teams, agent builders, security reviewers, model-risk teams, and auditors

## 1. Purpose

AI systems and agents increasingly create outputs that drive tickets, code changes, customer messages, legal drafts, operational decisions, and workflow actions. ETS can provide a verification layer around those AI events by recording hashes and metadata for prompts, retrieved context, tool calls, model outputs, reviewer actions, and policy routes.

This guide explains how to build AI governance evidence with ETS while avoiding a dangerous overclaim: ETS can verify submitted AI evidence material, but it cannot prove an AI output is correct, fair, safe, complete, legal, or unbiased.

## 2. Standards context

ETS can support AI risk management evidence by preserving proof-bearing records of AI workflow events. The guide is compatible with voluntary AI governance patterns such as NIST AI RMF 1.0, which is intended to improve incorporation of trustworthiness considerations into AI system design, development, use, and evaluation.

ETS should be treated as an evidence and replay layer beside AI governance controls, not a replacement for model evaluation, red teaming, legal review, human oversight, or domain validation.

## 3. AI evidence taxonomy

| Event type | Meaning | Hash target |
|---|---|---|
| `ai.prompt.submitted` | A user, system, or workflow prompt was submitted. | Prompt text or prompt packet. |
| `ai.context.retrieved` | RAG, search, connector, or document context was selected. | Retrieved context manifest. |
| `ai.tool_call.requested` | Agent requested a tool call. | Tool request JSON. |
| `ai.tool_call.completed` | Tool call returned status and output. | Tool response summary or output hash. |
| `ai.output.generated` | Model generated text, code, JSON, or action proposal. | Output artifact. |
| `ai.human_review.completed` | Human reviewed, approved, rejected, or edited. | Review packet. |
| `ai.policy.route` | Policy routed the AI event. | Routing decision. |
| `ai.release.published` | AI-derived output was published or deployed. | Publication manifest. |

## 4. Metadata to capture

```json
{
  "model_provider": "fictional-provider",
  "model_name": "fictional-model",
  "model_version": "demo",
  "system_prompt_hash": "sha256 hex string",
  "user_prompt_hash": "sha256 hex string",
  "context_manifest_hash": "sha256 hex string",
  "tool_names": ["github.create_issue"],
  "policy_version": "ai-policy-v1",
  "risk_tier": "medium",
  "human_review_required": true,
  "reviewer_role": "architect",
  "requested_action": "create_ticket",
  "sensitivity": "internal",
  "claim_boundary": "ETS verifies submitted AI workflow hashes and metadata only."
}
```

Do not store secrets, raw confidential prompts, private connector documents, customer records, PHI, legal records, or restricted evidence in public examples.

## 5. Python helper: hash AI artifacts

```python
from __future__ import annotations

from hashlib import sha256
from typing import Any


def sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def sha256_jsonish(value: Any) -> str:
    # For production use, prefer the ETS canonical JSON helper for structured payloads.
    from ets.core import canonical_sha256

    return canonical_sha256(value)
```

## 6. Build an AI EvidenceEvent

```python
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from ets.core import EvidenceEvent


def build_ai_output_event(
    *,
    tenant_id: str,
    workspace_id: str,
    correlation_id: str,
    prompt_text: str,
    output_text: str,
    model_name: str,
    policy_version: str,
    reviewer_required: bool,
    requested_action: str,
) -> EvidenceEvent:
    output_bytes = output_text.encode("utf-8")
    prompt_hash = sha256(prompt_text.encode("utf-8")).hexdigest()
    output_hash = sha256(output_bytes).hexdigest()

    return EvidenceEvent(
        event_id=f"evt-ai-output-{correlation_id}",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        evidence_id=f"ai-output-{correlation_id}",
        event_type="ai.output.generated",
        subject_ref=f"fictional://ai/{correlation_id}/output",
        content_hash=output_hash,
        content_hash_alg="sha256",
        metadata={
            "model_provider": "fictional-provider",
            "model_name": model_name,
            "model_version": "demo",
            "user_prompt_hash": prompt_hash,
            "context_manifest_hash": None,
            "tool_names": [],
            "policy_version": policy_version,
            "risk_tier": "medium",
            "human_review_required": reviewer_required,
            "requested_action": requested_action,
            "sensitivity": "internal",
            "claim_boundary": "ETS verifies submitted AI output hash and metadata only.",
        },
        created_at_utc=datetime.now(UTC),
        source_system="ai-governance-demo",
        actor_id="agent:demo",
        correlation_id=correlation_id,
        external_refs={"prompt_hash": prompt_hash, "output_hash": output_hash},
        redaction_profile="none",
    )
```

## 7. Record an agent tool call

```python
from ets.core import canonical_sha256


def build_tool_call_event(
    *,
    tenant_id: str,
    workspace_id: str,
    correlation_id: str,
    tool_name: str,
    request_payload: dict[str, object],
    allowed_by_policy: bool,
) -> EvidenceEvent:
    request_hash = canonical_sha256(request_payload)
    return EvidenceEvent(
        event_id=f"evt-ai-tool-request-{correlation_id}",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        evidence_id=f"ai-tool-request-{correlation_id}",
        event_type="ai.tool_call.requested",
        subject_ref=f"fictional://ai/{correlation_id}/tool/{tool_name}",
        content_hash=request_hash,
        content_hash_alg="sha256",
        metadata={
            "tool_name": tool_name,
            "tool_request_hash": request_hash,
            "allowed_by_policy": allowed_by_policy,
            "policy_boundary": "tool call may not execute until ETS proof and policy routing complete",
            "sensitivity": "internal",
        },
        created_at_utc=datetime.now(UTC),
        source_system="agent-orchestrator-demo",
        actor_id="agent:demo",
        correlation_id=correlation_id,
        external_refs={"tool_name": tool_name},
        redaction_profile="none",
    )
```

## 8. Full append, proof, certificate, route flow

```python
from ets.core import EvidenceProofBundle, InMemoryAppendOnlyLog, SignedTreeHead, generate_inclusion_proof
from ets.core.proofs import verify_inclusion_proof
from ets.reports.certificate import create_certificate
from datetime import UTC, datetime


def prove_ai_event(event: EvidenceEvent) -> dict[str, object]:
    log = InMemoryAppendOnlyLog()
    entry = log.append(event)
    proof = generate_inclusion_proof(log.list_entries(), entry.log_index)
    verification = verify_inclusion_proof(proof)

    tree_head = SignedTreeHead(
        tree_size=proof.tree_size,
        root_hash=proof.root_hash,
        created_at_utc=datetime.now(UTC),
        log_id="ets-ai-governance-demo",
        signature_alg=None,
        signature=None,
        public_key_id=None,
    )
    bundle = EvidenceProofBundle(
        event=entry.event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=tree_head,
        inclusion_proof=proof,
        verification_result=verification,
    )
    return {
        "verification": verification.model_dump(mode="json"),
        "certificate_markdown": create_certificate(bundle, "markdown"),
        "certificate_json": create_certificate(bundle, "json"),
    }
```

## 9. AI routing rules

```python
from docs.implementation.examples.routing import route_ets_evidence, RoutingRequest


def route_ai_event(event: EvidenceEvent, proof_valid: bool) -> str:
    metadata = dict(event.metadata)
    route = route_ets_evidence(
        RoutingRequest(
            event_id=event.event_id,
            event_type=event.event_type,
            tenant_id=event.tenant_id,
            workspace_id=event.workspace_id,
            proof_valid=proof_valid,
            tree_head_accepted=True,
            consistency_verified=True,
            requested_action=str(metadata.get("requested_action", "archive")),
            sensitivity=str(metadata.get("sensitivity", "internal")),
            external_release=bool(metadata.get("external_release", False)),
            civic_or_election_adjacent=False,
            source_system=event.source_system,
        )
    )
    return route.decision
```

If the AI event is external-facing, regulated, legal, medical, financial, civic, or safety-sensitive, default to `Human Review` even when proof is valid.

## 10. Certificate language

Use:

```text
This certificate verifies the submitted AI event hash, metadata, inclusion proof, tree-head material, verifier version, and policy route. It does not verify that the AI output is accurate, fair, safe, legally sufficient, unbiased, complete, or appropriate for deployment.
```

Do not use:

```text
ETS proves the AI answer is correct.
ETS certifies model safety.
ETS guarantees the agent acted properly.
ETS proves legal compliance.
```

## 11. Audit replay checklist

```text
[ ] Retrieve prompt hash and output hash.
[ ] Retrieve model/provider/version metadata.
[ ] Retrieve context manifest hash, if used.
[ ] Retrieve tool-call request and completion hashes.
[ ] Recompute event hash from EvidenceEvent metadata.
[ ] Verify inclusion proof.
[ ] Compare tree head and consistency proof, when available.
[ ] Review policy route.
[ ] Review human decision event.
[ ] Regenerate certificate and compare result.
```

## 12. Tests

```python
def test_ai_certificate_does_not_overclaim(certificate: str) -> None:
    lowered = certificate.lower()
    assert "does not verify" in lowered or "does not prove" in lowered
    assert "proves the ai answer is correct" not in lowered
    assert "guarantees" not in lowered


def test_ai_output_hash_changes_when_output_changes() -> None:
    event_a = build_ai_output_event(
        tenant_id="demo",
        workspace_id="ai",
        correlation_id="001",
        prompt_text="summarize fictional ticket",
        output_text="summary A",
        model_name="fictional-model",
        policy_version="ai-policy-v1",
        reviewer_required=True,
        requested_action="create_ticket",
    )
    event_b = build_ai_output_event(
        tenant_id="demo",
        workspace_id="ai",
        correlation_id="002",
        prompt_text="summarize fictional ticket",
        output_text="summary B",
        model_name="fictional-model",
        policy_version="ai-policy-v1",
        reviewer_required=True,
        requested_action="create_ticket",
    )
    assert event_a.content_hash != event_b.content_hash
```

## 13. References

- NIST AI RMF: `https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10`
- ETS Policy-Gated Routing Guide: `docs/implementation/ETS_POLICY_GATED_ROUTING_GUIDE.md`
- ETS Certificate and Public Verifier Guide: `docs/implementation/ETS_CERTIFICATE_PUBLIC_VERIFIER_GUIDE.md`
- ETS Audit Replay and Forensics Guide: `docs/implementation/ETS_AUDIT_REPLAY_FORENSICS_GUIDE.md`
