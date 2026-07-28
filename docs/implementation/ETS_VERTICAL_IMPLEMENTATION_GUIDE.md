# ETS Vertical Implementation Guide

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: architects, developers, integrators, demo builders, auditors, and product owners

ETS is the Evidence Transparency System. It is a transparency log and verification platform for provable digital evidence. This guide explains how to implement ETS across supported verticals using the current Python alpha surface, the local FastAPI API, and public-safe demo patterns.

This guide is intentionally practical. It tells an implementer what to capture, what to hash, what not to store, how to route evidence states, and how to build working Python examples without leaking private evidence, secrets, official records, USPTO filing material, claim charts, or attorney-review material.

## Public-safe claim boundary

ETS verifies submitted-event metadata, content hashes, inclusion proofs, tree-head progression, verification certificates, and policy-routing records within defined protocol boundaries.

ETS does not prove real-world truth, legal sufficiency, official chain of custody, election correctness, vote totals, ballot validity, raw evidence authenticity, or completeness without an external expected-event policy and observation process.

All examples in this guide use fictional, local-only, non-PII data.

## Research and standards context

ETS should be implemented as a verification and evidence-routing layer, not as a replacement for the frameworks below.

| Area | Relevant source | Implementation takeaway for ETS |
|---|---|---|
| AI governance | NIST AI RMF 1.0 describes voluntary AI risk management guidance to improve trustworthiness considerations in design, development, use, and evaluation of AI systems. | ETS can record AI evidence events such as prompt hashes, model identifiers, tool calls, output hashes, reviewer decisions, and policy versions. |
| Secure software development | NIST SP 800-218 SSDF defines high-level secure software development practices that can be integrated into SDLC implementations. | ETS can attach verifiable evidence to build, scan, SBOM, release, deployment, and approval events. |
| Audit and compliance | NIST SP 800-53 and similar control frameworks use audit events, accountability, and evidence review patterns. | ETS should produce replayable proof material for audit events instead of replacing the control framework. |
| Healthcare audit controls | HHS HIPAA audit protocol references audit controls that record and examine activity in information systems containing or using ePHI, and information system activity review such as audit logs, access reports, and incident tracking reports. | ETS examples must store hashes and metadata only, not raw PHI or ePHI. |
| Insurance AI governance | NAIC materials describe AI governance and risk management expectations for insurers, including governance controls and written AIS program expectations in the Model Bulletin context. | ETS can provide evidence packets for AI-assisted underwriting, claims, consumer notices, and review actions. |
| Cybersecurity disclosure | SEC cybersecurity rules address risk management, strategy, governance, and incident disclosure by public companies. | ETS can support materiality-review evidence, incident decision packets, disclosure sign-off, and board-reporting audit trails. |
| Zero Trust | CISA Zero Trust Maturity Model uses pillars such as identity, devices, networks, applications/workloads, and data, with cross-cutting visibility and analytics, automation and orchestration, and governance. | ETS can provide proof-bearing evidence for visibility, automation, governance, and policy-gated decisions. |

Sources used while drafting this guide: NIST AI RMF 1.0, NIST SP 800-218 SSDF, HHS HIPAA audit protocol, NAIC AI materials, SEC cybersecurity disclosure materials, and CISA Zero Trust Maturity Model.

## Supported verticals

This guide covers these supported ETS verticals:

1. AI governance and agent accountability
2. DevSecOps and software supply chain
3. Enterprise compliance, audit, and security operations
4. Healthcare and life sciences evidence
5. Insurance claims, underwriting, and AI-assisted decisions
6. Financial operations, fraud, payments, and disclosure workflows
7. Public-sector, civic, and election-adjacent audit packets
8. Emergency, outage, sensor, RF, and IoT evidence
9. Legal, HR, employment, and dispute evidence
10. Lantern ecosystem integrations: SignalForge, Christina, OpsHelm, GitHub, and Lantern-Civic

Each vertical follows the same ETS pattern:

```text
source event
  -> hash raw artifact outside ETS
  -> build EvidenceEvent metadata
  -> validate schema
  -> canonicalize hashable payload
  -> append to ETS log
  -> generate inclusion proof
  -> build proof bundle
  -> generate verification certificate
  -> policy route
  -> replay later
```

## ETS building blocks

The alpha implementation exposes these building blocks:

| Component | Role |
|---|---|
| `EvidenceEvent` | Stable metadata contract for hashable evidence metadata. |
| `canonical_sha256` | Deterministic SHA-256 over canonical JSON. |
| `InMemoryAppendOnlyLog` | Local append-only log for tests and demos. |
| `SQLiteEventStore` | Local durable store for validation and smoke testing. |
| `generate_inclusion_proof` | Build a Merkle inclusion proof for a log entry. |
| `verify_inclusion_proof` | Recompute the proof path and verify the stated root. |
| `generate_consistency_proof` | Show tree-head progression between sizes. |
| `verify_consistency_proof` | Validate progression evidence. |
| `EvidenceProofBundle` | Offline verification bundle containing event, hashes, tree head, proof, and verification result. |
| `create_certificate` | Produce claim-safe JSON, Markdown, or HTML verification certificates. |
| `/api/v1/events` | Local API append endpoint. |
| `/api/v1/bundles/{event_id}` | Proof bundle endpoint. |
| `/reports/certificate` | Certificate endpoint. |
| `/lab` | Local Python testing lab UI. |

## Environment setup

Install and run the repo in a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run the local ETS API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

Run the Python testing lab UI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.lab.app:app --reload --port 8100
```

Open:

```text
http://localhost:8100/lab
```

For local durable testing:

```powershell
$env:ETS_STORAGE_PROVIDER = "sqlite"
$env:ETS_SQLITE_PATH = ".data\ets.db"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

## Core implementation pattern

### Step 1: keep raw evidence outside ETS unless the deployment owner approves storage

The safest default is to store raw evidence in the source system or an approved evidence store and send ETS only:

```text
content hash
metadata
source reference
tenant and workspace
actor or system id
correlation id
policy context
redaction profile
```

Never send these in public examples:

```text
secrets
API tokens
private keys
real PII
real PHI/ePHI
production customer evidence
official election data
legal records
medical records
financial account records
USPTO receipts
application numbers
claim charts
attorney-review notes
```

### Step 2: hash the source artifact

```python
from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


artifact_hash = sha256_file("sample-artifacts/fictional-review.json")
print(artifact_hash)
```

For an in-memory artifact:

```python
from hashlib import sha256

raw_bytes = b"fictional lab artifact only"
artifact_hash = sha256(raw_bytes).hexdigest()
```

### Step 3: create an EvidenceEvent

```python
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from ets.core import EvidenceEvent


def make_event(
    *,
    event_id: str,
    tenant_id: str,
    workspace_id: str,
    evidence_id: str,
    event_type: str,
    subject_ref: str,
    raw_artifact_bytes: bytes,
    metadata: dict[str, object],
    source_system: str,
    actor_id: str,
    correlation_id: str,
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        evidence_id=evidence_id,
        event_type=event_type,
        subject_ref=subject_ref,
        content_hash=sha256(raw_artifact_bytes).hexdigest(),
        content_hash_alg="sha256",
        metadata=metadata,
        created_at_utc=datetime.now(UTC),
        source_system=source_system,
        actor_id=actor_id,
        correlation_id=correlation_id,
        external_refs={"artifact_uri": subject_ref},
        redaction_profile="none",
    )
```

### Step 4: append locally in Python

```python
from ets.core import InMemoryAppendOnlyLog, canonical_sha256

log = InMemoryAppendOnlyLog()
event = make_event(
    event_id="evt-demo-001",
    tenant_id="demo-tenant",
    workspace_id="implementation-guide",
    evidence_id="evidence-demo-001",
    event_type="workflow.evidence",
    subject_ref="fictional://implementation-guide/demo-001",
    raw_artifact_bytes=b"fictional evidence payload",
    metadata={"risk": "medium", "review_required": True},
    source_system="implementation-guide",
    actor_id="developer",
    correlation_id="demo-run-001",
)

entry = log.append(event)
print(entry.log_index)
print(entry.event_hash)
print(entry.leaf_hash)
print(canonical_sha256(event.hashable_payload()))
```

### Step 5: generate and verify an inclusion proof

```python
from ets.core import generate_inclusion_proof
from ets.core.proofs import verify_inclusion_proof

proof = generate_inclusion_proof(log.list_entries(), entry.log_index)
verification = verify_inclusion_proof(proof)

assert verification.valid, verification.reason
print(proof.root_hash)
print(verification.reason)
```

### Step 6: create a proof bundle and certificate

```python
from datetime import UTC, datetime

from ets.core import EvidenceProofBundle, SignedTreeHead
from ets.reports.certificate import create_certificate

tree_head = SignedTreeHead(
    tree_size=proof.tree_size,
    root_hash=proof.root_hash,
    created_at_utc=datetime.now(UTC),
    log_id="ets-local-guide",
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

markdown_certificate = create_certificate(bundle, "markdown")
html_certificate = create_certificate(bundle, "html")
json_certificate = create_certificate(bundle, "json")

print(markdown_certificate)
```

### Step 7: append through the local API

The local API expects an `EvidenceEvent` JSON payload.

```python
from __future__ import annotations

import httpx


def append_event_api(base_url: str, event: EvidenceEvent) -> dict[str, object]:
    response = httpx.post(
        f"{base_url}/api/v1/events",
        json=event.model_dump(mode="json"),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


append_response = append_event_api("http://localhost:8000", event)
print(append_response["event_id"])
print(append_response["inclusion_proof_url"])
```

### Step 8: request a proof bundle and certificate through the API

```python
import httpx

base_url = "http://localhost:8000"
event_id = append_response["event_id"]

bundle_response = httpx.get(f"{base_url}/api/v1/bundles/{event_id}", timeout=15)
bundle_response.raise_for_status()
bundle_json = bundle_response.json()

certificate_response = httpx.post(
    f"{base_url}/reports/certificate",
    json={"bundle": bundle_json, "format": "markdown"},
    timeout=15,
)
certificate_response.raise_for_status()
print(certificate_response.json()["content"])
```

## Shared helper module for vertical integrations

Create a local helper file in your application, not necessarily in ETS itself:

```python
# app/ets_client.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from ets.core import EvidenceEvent


@dataclass(frozen=True)
class ETSClient:
    base_url: str
    timeout_seconds: float = 15.0

    def build_event(
        self,
        *,
        event_id: str,
        tenant_id: str,
        workspace_id: str,
        evidence_id: str,
        event_type: str,
        subject_ref: str,
        artifact_bytes: bytes,
        metadata: dict[str, Any],
        source_system: str,
        actor_id: str,
        correlation_id: str,
        redaction_profile: str = "none",
    ) -> EvidenceEvent:
        return EvidenceEvent(
            event_id=event_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            evidence_id=evidence_id,
            event_type=event_type,
            subject_ref=subject_ref,
            content_hash=sha256(artifact_bytes).hexdigest(),
            content_hash_alg="sha256",
            metadata=metadata,
            created_at_utc=datetime.now(UTC),
            source_system=source_system,
            actor_id=actor_id,
            correlation_id=correlation_id,
            external_refs={"subject_ref": subject_ref},
            redaction_profile=redaction_profile,
        )

    def append_event(self, event: EvidenceEvent) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/api/v1/events",
            json=event.model_dump(mode="json"),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def get_bundle(self, event_id: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.base_url}/api/v1/bundles/{event_id}",
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def certificate(self, bundle: dict[str, Any], output_format: str = "markdown") -> str:
        response = httpx.post(
            f"{self.base_url}/reports/certificate",
            json={"bundle": bundle, "format": output_format},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return str(response.json()["content"])
```

## Policy-gated routing baseline

ETS should not let a valid proof automatically trigger every downstream action. Route by proof status, sensitivity, request type, tenant policy, and claim boundary.

```python
from __future__ import annotations

from typing import Literal

Decision = Literal[
    "Automation Approval",
    "Human Review",
    "Quarantine / Reject",
    "Archive / Restrict Release",
]


def route_evidence(
    *,
    proof_valid: bool,
    requested_action: str,
    sensitivity: str,
    external_release: bool,
    civic_or_election_adjacent: bool,
) -> dict[str, str]:
    if not proof_valid:
        return {
            "decision": "Quarantine / Reject",
            "required_state": "Requires Human Review",
            "reason": "proof material is invalid, missing, or root-mismatched",
        }

    if civic_or_election_adjacent:
        return {
            "decision": "Human Review",
            "required_state": "Public Release Restricted",
            "reason": "civic/election-adjacent evidence requires non-claim review boundary",
        }

    if sensitivity in {"restricted", "confidential", "regulated"} or external_release:
        return {
            "decision": "Human Review",
            "required_state": "Public Release Restricted",
            "reason": "verified proof material is sensitive or externally visible",
        }

    if requested_action in {"trigger_automation", "create_ticket", "approve_release"}:
        return {
            "decision": "Automation Approval",
            "required_state": "Hash Verified + Inclusion Proof Verified",
            "reason": "proof material verified and no sensitive release flag is present",
        }

    return {
        "decision": "Archive / Restrict Release",
        "required_state": "Archived",
        "reason": "verified evidence retained for audit replay",
    }
```

## Vertical 1: AI governance and agent accountability

### When to use ETS

Use ETS when an AI system or agent produces a decision, recommendation, tool call, user-facing output, code change, risk score, workflow approval, or policy-sensitive action.

### Evidence events to capture

| Event type | Meaning |
|---|---|
| `ai.prompt.submitted` | A prompt or task request was submitted. Store a hash, not the raw prompt if sensitive. |
| `ai.context.retrieved` | RAG, search, connector, or document context was used. |
| `ai.tool_call.requested` | Agent requested a tool call. |
| `ai.tool_call.completed` | Tool call completed with status and output hash. |
| `ai.output.generated` | Model produced output. |
| `ai.human_review.completed` | Human approved, rejected, edited, or escalated output. |
| `ai.policy.route` | Policy engine routed the AI event. |

### Required metadata

```json
{
  "model_provider": "fictional-provider",
  "model_name": "fictional-model",
  "model_version": "demo",
  "prompt_hash": "sha256 hex string",
  "context_hashes": ["sha256 hex string"],
  "tool_names": ["github.create_issue"],
  "policy_version": "ai-policy-2026-06-demo",
  "risk_tier": "medium",
  "human_review_required": true,
  "reviewer_role": "architect"
}
```

### Python example

```python
from __future__ import annotations

from hashlib import sha256

from app.ets_client import ETSClient


def record_ai_output(
    *,
    ets: ETSClient,
    output_text: str,
    prompt_text: str,
    tenant_id: str,
    workspace_id: str,
    correlation_id: str,
) -> dict[str, object]:
    output_bytes = output_text.encode("utf-8")
    prompt_hash = sha256(prompt_text.encode("utf-8")).hexdigest()

    event = ets.build_event(
        event_id=f"evt-ai-output-{correlation_id}",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        evidence_id=f"ai-output-{correlation_id}",
        event_type="ai.output.generated",
        subject_ref=f"fictional://ai/{correlation_id}/output",
        artifact_bytes=output_bytes,
        metadata={
            "model_provider": "fictional-provider",
            "model_name": "fictional-model",
            "model_version": "demo",
            "prompt_hash": prompt_hash,
            "context_hashes": [],
            "tool_names": [],
            "policy_version": "ai-policy-2026-06-demo",
            "risk_tier": "medium",
            "human_review_required": True,
            "claim_boundary": "ETS verifies submitted AI output hash and metadata only.",
        },
        source_system="ai-agent-demo",
        actor_id="agent:demo",
        correlation_id=correlation_id,
    )

    append_result = ets.append_event(event)
    bundle = ets.get_bundle(str(append_result["event_id"]))
    certificate = ets.certificate(bundle, "markdown")
    return {
        "append_result": append_result,
        "bundle": bundle,
        "certificate": certificate,
    }
```

### Routing rules

```python
routing = route_evidence(
    proof_valid=True,
    requested_action="external_release",
    sensitivity="regulated",
    external_release=True,
    civic_or_election_adjacent=False,
)
assert routing["decision"] == "Human Review"
```

### What the certificate should say

```text
This certificate verifies the submitted AI event payload hash, inclusion proof, tree-head material, and verifier version. It does not verify that the AI output is correct, fair, safe, legally sufficient, or complete.
```

## Vertical 2: DevSecOps and software supply chain

### When to use ETS

Use ETS when a build, scan, SBOM, release approval, deployment, rollback, dependency update, or GitHub PR event becomes evidence for later verification.

### Evidence events to capture

| Event type | Evidence example |
|---|---|
| `git.pr.opened` | PR metadata hash, branch, commit SHA, author id. |
| `git.pr.reviewed` | Review decision and reviewer role. |
| `ci.build.completed` | Build result hash and workflow run id. |
| `security.scan.completed` | Scanner summary hash and severity counts. |
| `sbom.generated` | SBOM file hash and generator version. |
| `release.approved` | Approval packet and sign-off hash. |
| `deployment.completed` | Deployment manifest hash. |

### Metadata pattern

```json
{
  "repo": "ShannonBrayNC/ETS",
  "commit_sha": "fictionalsha0000000000000000000000000000000000",
  "workflow_run_id": "demo-run-001",
  "artifact_hashes": {
    "sbom": "sha256 hex",
    "test_report": "sha256 hex"
  },
  "ssdf_mapping": ["PO", "PS", "PW", "RV"],
  "release_gate": "alpha-public-boundary"
}
```

### Python example

```python
from __future__ import annotations

import json
from hashlib import sha256

from app.ets_client import ETSClient


def record_ci_build(
    ets: ETSClient,
    *,
    repo: str,
    commit_sha: str,
    workflow_run_id: str,
    test_summary: dict[str, object],
) -> dict[str, object]:
    artifact_bytes = json.dumps(test_summary, sort_keys=True, separators=(",", ":")).encode()
    test_report_hash = sha256(artifact_bytes).hexdigest()

    event = ets.build_event(
        event_id=f"evt-ci-build-{workflow_run_id}",
        tenant_id="demo-tenant",
        workspace_id="devsecops",
        evidence_id=f"ci-build-{workflow_run_id}",
        event_type="ci.build.completed",
        subject_ref=f"fictional://github/{repo}/actions/{workflow_run_id}",
        artifact_bytes=artifact_bytes,
        metadata={
            "repo": repo,
            "commit_sha": commit_sha,
            "workflow_run_id": workflow_run_id,
            "test_report_hash": test_report_hash,
            "ssdf_mapping": ["PO", "PS", "PW", "RV"],
            "release_gate": "alpha-public-boundary",
            "claim_boundary": "ETS verifies build evidence packet inclusion, not source-code safety by itself.",
        },
        source_system="github-actions",
        actor_id="ci:github-actions",
        correlation_id=f"ci-{workflow_run_id}",
    )
    append_result = ets.append_event(event)
    return {
        "append_result": append_result,
        "bundle": ets.get_bundle(str(append_result["event_id"])),
    }
```

### Policy routing

| Condition | Route |
|---|---|
| Proof valid, test passed, no public release | Automation Approval |
| Proof valid, public release | Human Review |
| Proof invalid | Quarantine / Reject |
| Missing SBOM or scan | Human Review |
| Security severity over threshold | Human Review or Reject |

## Vertical 3: Enterprise compliance, audit, and security operations

### When to use ETS

Use ETS when control evidence, access reviews, incident records, policy exceptions, or security operations actions must be reproducible later.

### Evidence events

```text
access.review.completed
privileged.access.granted
policy.exception.requested
policy.exception.approved
incident.evidence.added
incident.timeline.updated
control.attestation.submitted
risk.acceptance.approved
```

### Code example: access review evidence

```python
from __future__ import annotations

import json
from hashlib import sha256

from app.ets_client import ETSClient


def record_access_review(
    ets: ETSClient,
    *,
    review_id: str,
    system_id: str,
    reviewer_id: str,
    decision_counts: dict[str, int],
) -> dict[str, object]:
    packet = {
        "review_id": review_id,
        "system_id": system_id,
        "decision_counts": decision_counts,
        "fictional": True,
    }
    packet_bytes = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()

    event = ets.build_event(
        event_id=f"evt-access-review-{review_id}",
        tenant_id="demo-tenant",
        workspace_id="enterprise-compliance",
        evidence_id=f"access-review-{review_id}",
        event_type="access.review.completed",
        subject_ref=f"fictional://iam/access-reviews/{review_id}",
        artifact_bytes=packet_bytes,
        metadata={
            "system_id": system_id,
            "reviewer_id": reviewer_id,
            "packet_hash": sha256(packet_bytes).hexdigest(),
            "control_family": "Audit and Accountability",
            "retention_profile": "local-demo",
            "claim_boundary": "ETS verifies the submitted access review packet hash, not whether every access right was reviewed.",
        },
        source_system="identity-governance-demo",
        actor_id=reviewer_id,
        correlation_id=f"access-review-{review_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### Operational notes

For enterprise audits, use tenant/workspace scoping. A good pattern is:

```text
tenant_id = organization or legal entity
workspace_id = audit program, product, business unit, or environment
evidence_id = stable artifact identifier
event_id = immutable occurrence id
correlation_id = incident, review, request, or control id
```

## Vertical 4: Healthcare and life sciences

### When to use ETS

Use ETS for metadata and hashes around consent records, care workflow checkpoints, lab workflow events, device records, data-export approvals, and research data handling. Do not store raw PHI or ePHI in public examples.

### Evidence events

```text
health.consent.hash_recorded
health.data_export.approved
health.lab_observation.hash_recorded
health.device_event.hash_recorded
health.access_review.completed
life_sciences.protocol_version.approved
life_sciences.sample_chain_event.hash_recorded
```

### Metadata pattern

```json
{
  "regulated_data": true,
  "raw_record_location": "external-system-only",
  "content_classification": "ePHI-hash-only-demo",
  "minimum_necessary": true,
  "reviewer_role": "privacy-officer",
  "claim_boundary": "ETS verifies submitted hash and metadata only. It does not store or validate raw PHI."
}
```

### Code example: consent record hash

```python
from __future__ import annotations

from app.ets_client import ETSClient


def record_consent_hash(
    ets: ETSClient,
    *,
    consent_id: str,
    consent_pdf_bytes: bytes,
    reviewer_id: str,
) -> dict[str, object]:
    event = ets.build_event(
        event_id=f"evt-consent-{consent_id}",
        tenant_id="demo-health-tenant",
        workspace_id="healthcare-hash-only",
        evidence_id=f"consent-{consent_id}",
        event_type="health.consent.hash_recorded",
        subject_ref=f"external-ehr://consent/{consent_id}",
        artifact_bytes=consent_pdf_bytes,
        metadata={
            "regulated_data": True,
            "raw_record_location": "external-system-only",
            "content_classification": "ePHI-hash-only-demo",
            "minimum_necessary": True,
            "reviewer_role": "privacy-officer",
            "claim_boundary": "ETS verifies the submitted consent hash and metadata only, not legal sufficiency of consent.",
        },
        source_system="ehr-demo-adapter",
        actor_id=reviewer_id,
        correlation_id=f"consent-{consent_id}",
        redaction_profile="strict",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### Safety rules

```text
Do not put patient name in metadata.
Do not put date of birth in metadata.
Do not put medical record number in metadata.
Do not put diagnosis text in metadata.
Use external references that are meaningful only inside the covered system.
Use strict redaction profiles when available.
```

## Vertical 5: Insurance claims, underwriting, and AI-assisted decisions

### When to use ETS

Use ETS to capture claim packets, photo hashes, adjuster notes hashes, policy document hashes, consumer notice hashes, AI score metadata, underwriting review actions, and appeal events.

### Evidence events

```text
insurance.claim.opened
insurance.claim.photo_hash_recorded
insurance.adjuster.review_completed
insurance.ai_score.generated
insurance.coverage.decision_recorded
insurance.consumer_notice.sent
insurance.appeal.received
insurance.appeal.reviewed
```

### Code example: claim photo packet

```python
from __future__ import annotations

from app.ets_client import ETSClient


def record_claim_photo_hash(
    ets: ETSClient,
    *,
    claim_id: str,
    photo_id: str,
    photo_bytes: bytes,
    adjuster_id: str,
) -> dict[str, object]:
    event = ets.build_event(
        event_id=f"evt-claim-photo-{claim_id}-{photo_id}",
        tenant_id="demo-insurer",
        workspace_id="claims",
        evidence_id=f"claim-photo-{claim_id}-{photo_id}",
        event_type="insurance.claim.photo_hash_recorded",
        subject_ref=f"claims-system://claims/{claim_id}/photos/{photo_id}",
        artifact_bytes=photo_bytes,
        metadata={
            "claim_id_hash_only": True,
            "photo_id": photo_id,
            "adjuster_id": adjuster_id,
            "consumer_impacting_decision": False,
            "ai_assisted": False,
            "claim_boundary": "ETS verifies the submitted claim-photo hash and metadata only, not cause of loss or coverage.",
        },
        source_system="claims-demo",
        actor_id=adjuster_id,
        correlation_id=f"claim-{claim_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### Code example: AI-assisted insurance score

```python
from __future__ import annotations

import json

from app.ets_client import ETSClient


def record_insurance_ai_score(
    ets: ETSClient,
    *,
    decision_id: str,
    model_version: str,
    score_packet: dict[str, object],
    reviewer_id: str,
) -> dict[str, object]:
    packet_bytes = json.dumps(score_packet, sort_keys=True, separators=(",", ":")).encode()
    event = ets.build_event(
        event_id=f"evt-insurance-ai-score-{decision_id}",
        tenant_id="demo-insurer",
        workspace_id="ai-governance",
        evidence_id=f"insurance-ai-score-{decision_id}",
        event_type="insurance.ai_score.generated",
        subject_ref=f"claims-system://ai-decisions/{decision_id}",
        artifact_bytes=packet_bytes,
        metadata={
            "model_version": model_version,
            "consumer_impacting_decision": True,
            "human_review_required": True,
            "reviewer_id": reviewer_id,
            "governance_program": "AIS Program demo",
            "claim_boundary": "ETS verifies the AI score packet hash and review metadata only, not fairness, accuracy, or coverage legality.",
        },
        source_system="insurance-ai-demo",
        actor_id="model:insurance-demo",
        correlation_id=f"insurance-decision-{decision_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

## Vertical 6: Financial operations, fraud, payments, and disclosure workflows

### When to use ETS

Use ETS for payment approval evidence, fraud review packets, chargeback packets, reconciliation events, materiality-review evidence, cybersecurity incident governance, disclosure review, and board reporting packages.

### Evidence events

```text
finance.payment.approved
finance.reconciliation.completed
finance.fraud_review.opened
finance.fraud_review.closed
finance.chargeback.packet_hash_recorded
cyber.incident.materiality_review.started
cyber.incident.materiality_decision.recorded
cyber.disclosure.review.completed
board.cyber_report.packet_hash_recorded
```

### Code example: materiality decision packet

```python
from __future__ import annotations

import json

from app.ets_client import ETSClient


def record_cyber_materiality_decision(
    ets: ETSClient,
    *,
    incident_id: str,
    decision_packet: dict[str, object],
    decision_owner: str,
) -> dict[str, object]:
    packet_bytes = json.dumps(decision_packet, sort_keys=True, separators=(",", ":")).encode()
    event = ets.build_event(
        event_id=f"evt-cyber-materiality-{incident_id}",
        tenant_id="demo-finance",
        workspace_id="cyber-governance",
        evidence_id=f"materiality-decision-{incident_id}",
        event_type="cyber.incident.materiality_decision.recorded",
        subject_ref=f"incident-system://incidents/{incident_id}/materiality",
        artifact_bytes=packet_bytes,
        metadata={
            "incident_id": incident_id,
            "decision_owner": decision_owner,
            "board_report_required": True,
            "external_disclosure_review": True,
            "legal_review_required": True,
            "claim_boundary": "ETS verifies the submitted materiality-decision packet hash, not the legal correctness of disclosure decisions.",
        },
        source_system="cyber-governance-demo",
        actor_id=decision_owner,
        correlation_id=f"incident-{incident_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### Routing rules

```text
proof invalid -> Quarantine / Reject
proof valid + material incident -> Human Review
proof valid + board-report packet -> Human Review
proof valid + routine reconciliation -> Archive / Restrict Release
proof valid + non-sensitive operational packet -> Automation Approval
```

## Vertical 7: Public-sector, civic, and election-adjacent audit packets

### When to use ETS

Use ETS for public-record packet hashes, civic audit artifacts, observer note hashes, procurement decision evidence, public meeting packet hashes, and fictional election-adjacent demos. Be precise and restrained.

### Required boundary

Every civic/election-adjacent implementation must repeat:

```text
ETS is not voting software, tabulation software, voter registration software, ballot software, ballot-counting software, election correctness software, or the vote of record unless separately certified and legally designated.
```

### Evidence events

```text
civic.public_record.packet_hash_recorded
civic.audit_report.published
civic.observer_note.hash_recorded
civic.procurement.decision_recorded
civic.meeting_packet.hash_recorded
election_adjacent.demo_packet.hash_recorded
```

### Code example: civic audit packet

```python
from __future__ import annotations

import json

from app.ets_client import ETSClient

CIVIC_BOUNDARY = (
    "ETS verifies submitted-event metadata and proof material only. "
    "ETS is not voting software, tabulation software, voter registration software, "
    "ballot software, election correctness software, or the vote of record unless "
    "separately certified and legally designated."
)


def record_civic_audit_packet(
    ets: ETSClient,
    *,
    packet_id: str,
    packet: dict[str, object],
    publisher_id: str,
) -> dict[str, object]:
    packet_bytes = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
    event = ets.build_event(
        event_id=f"evt-civic-audit-{packet_id}",
        tenant_id="demo-civic",
        workspace_id="public-audit",
        evidence_id=f"civic-audit-{packet_id}",
        event_type="civic.audit_report.published",
        subject_ref=f"fictional://civic/audit/{packet_id}",
        artifact_bytes=packet_bytes,
        metadata={
            "fictional": True,
            "public_release_restricted": True,
            "human_review_required": True,
            "non_claim_boundary": CIVIC_BOUNDARY,
        },
        source_system="lantern-civic-demo",
        actor_id=publisher_id,
        correlation_id=f"civic-audit-{packet_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### Routing rule

```python
route = route_evidence(
    proof_valid=True,
    requested_action="external_release",
    sensitivity="restricted",
    external_release=True,
    civic_or_election_adjacent=True,
)
assert route["decision"] == "Human Review"
```

## Vertical 8: Emergency, outage, sensor, RF, and IoT evidence

### When to use ETS

Use ETS for emergency reports, outage records, RF anomaly records, telemetry packets, weather-impact records, dispatch checkpoints, and escalation logs. Store hashes and normalized metadata, not sensitive raw streams.

### Evidence events

```text
emergency.report.hash_recorded
outage.record.hash_recorded
sensor.telemetry.hash_recorded
rf.anomaly.detected
weather.impact.packet_hash_recorded
dispatch.escalation.recorded
field.response.checkpoint_recorded
```

### Code example: sensor telemetry hash

```python
from __future__ import annotations

import json

from app.ets_client import ETSClient


def record_sensor_packet(
    ets: ETSClient,
    *,
    sensor_id: str,
    packet_id: str,
    reading_packet: dict[str, object],
) -> dict[str, object]:
    packet_bytes = json.dumps(reading_packet, sort_keys=True, separators=(",", ":")).encode()
    event = ets.build_event(
        event_id=f"evt-sensor-{sensor_id}-{packet_id}",
        tenant_id="demo-emergency",
        workspace_id="sensor-evidence",
        evidence_id=f"sensor-{sensor_id}-{packet_id}",
        event_type="sensor.telemetry.hash_recorded",
        subject_ref=f"sensor-store://{sensor_id}/{packet_id}",
        artifact_bytes=packet_bytes,
        metadata={
            "sensor_id": sensor_id,
            "packet_id": packet_id,
            "telemetry_hash_only": True,
            "routing": "escalate_on_threshold_or_anomaly",
            "claim_boundary": "ETS verifies the submitted telemetry packet hash and metadata only, not physical-world correctness of the sensor.",
        },
        source_system="sensor-demo-adapter",
        actor_id=f"sensor:{sensor_id}",
        correlation_id=f"sensor-{sensor_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### Recommended metadata fields

```json
{
  "sensor_id": "fictional-sensor-001",
  "packet_id": "pkt-001",
  "calibration_profile_hash": "sha256 hex",
  "location_bucket": "coarse-grid-only",
  "raw_stream_retained_outside_ets": true,
  "operator_review_required": true
}
```

## Vertical 9: Legal, HR, employment, and dispute evidence

### When to use ETS

Use ETS for document receipt hashes, employee notice hashes, wage record packets, accommodation request packet hashes, case notes, dispute correspondence, review actions, and timeline reconstruction.

ETS should not claim court admissibility, legal sufficiency, or official chain of custody. It verifies submitted hash and proof material only.

### Evidence events

```text
legal.document.received_hash_recorded
legal.correspondence.sent_hash_recorded
hr.notice.sent_hash_recorded
hr.accommodation.request_hash_recorded
hr.review.action_recorded
wage.record.packet_hash_recorded
dispute.timeline.updated
```

### Code example: document receipt

```python
from __future__ import annotations

from app.ets_client import ETSClient


def record_document_receipt(
    ets: ETSClient,
    *,
    matter_id: str,
    document_id: str,
    document_bytes: bytes,
    receiver_id: str,
) -> dict[str, object]:
    event = ets.build_event(
        event_id=f"evt-doc-received-{matter_id}-{document_id}",
        tenant_id="demo-legal",
        workspace_id="dispute-evidence",
        evidence_id=f"document-{document_id}",
        event_type="legal.document.received_hash_recorded",
        subject_ref=f"matter-store://{matter_id}/documents/{document_id}",
        artifact_bytes=document_bytes,
        metadata={
            "matter_id": matter_id,
            "document_id": document_id,
            "receiver_id": receiver_id,
            "raw_document_location": "external-matter-store",
            "legal_review_required": True,
            "claim_boundary": "ETS verifies receipt packet hash and metadata only, not admissibility or legal sufficiency.",
        },
        source_system="matter-demo",
        actor_id=receiver_id,
        correlation_id=f"matter-{matter_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

## Vertical 10: Lantern ecosystem integrations

### SignalForge

Use ETS to verify recommendations, deployment plans, Azure configuration evidence, policy decisions, and generated plan artifacts before they influence automation.

```python
def record_signalforge_recommendation(
    ets: ETSClient,
    *,
    recommendation_id: str,
    recommendation_bytes: bytes,
    actor_id: str,
) -> dict[str, object]:
    event = ets.build_event(
        event_id=f"evt-signalforge-{recommendation_id}",
        tenant_id="lantern",
        workspace_id="signalforge",
        evidence_id=f"recommendation-{recommendation_id}",
        event_type="signalforge.recommendation.generated",
        subject_ref=f"signalforge://recommendations/{recommendation_id}",
        artifact_bytes=recommendation_bytes,
        metadata={
            "requires_policy_gate": True,
            "allowed_routes": ["human_review", "automation_approval", "quarantine"],
            "claim_boundary": "ETS verifies recommendation hash and proof material only, not infrastructure correctness.",
        },
        source_system="SignalForge",
        actor_id=actor_id,
        correlation_id=f"signalforge-{recommendation_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### Christina

Use ETS to verify orchestration approvals, natural-language-to-workflow conversions, agent task plans, and reviewer approvals.

```python
def record_christina_approval(
    ets: ETSClient,
    *,
    approval_id: str,
    approval_packet: bytes,
    reviewer_id: str,
) -> dict[str, object]:
    event = ets.build_event(
        event_id=f"evt-christina-approval-{approval_id}",
        tenant_id="lantern",
        workspace_id="christina",
        evidence_id=f"approval-{approval_id}",
        event_type="christina.approval.completed",
        subject_ref=f"christina://approvals/{approval_id}",
        artifact_bytes=approval_packet,
        metadata={
            "reviewer_id": reviewer_id,
            "human_review_required": True,
            "automation_may_follow": True,
            "claim_boundary": "ETS verifies approval packet hash and proof material only, not business correctness of the approval.",
        },
        source_system="Christina",
        actor_id=reviewer_id,
        correlation_id=f"christina-{approval_id}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### OpsHelm

Use ETS to verify ticket analysis, log analysis summaries, customer impact assessments, escalation decisions, and auto-follow-up drafts before they are sent or routed.

```python
def record_opshelm_finding(
    ets: ETSClient,
    *,
    ticket_id: str,
    finding_bytes: bytes,
    analyst_id: str,
) -> dict[str, object]:
    event = ets.build_event(
        event_id=f"evt-opshelm-finding-{ticket_id}",
        tenant_id="lantern",
        workspace_id="opshelm",
        evidence_id=f"opshelm-finding-{ticket_id}",
        event_type="opshelm.finding.generated",
        subject_ref=f"opshelm://tickets/{ticket_id}/findings/latest",
        artifact_bytes=finding_bytes,
        metadata={
            "ticket_id": ticket_id,
            "customer_data_excluded": True,
            "human_review_required_before_customer_send": True,
            "claim_boundary": "ETS verifies finding hash and proof material only, not support accuracy or customer entitlement.",
        },
        source_system="OpsHelm",
        actor_id=analyst_id,
        correlation_id=f"ticket-{ticket_id}",
        redaction_profile="basic_pii",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

### GitHub

Use ETS to verify issue creation, PR recommendation, release gate output, and CI evidence.

```python
def record_github_pr_evidence(
    ets: ETSClient,
    *,
    repo: str,
    pr_number: int,
    commit_sha: str,
    pr_summary_bytes: bytes,
) -> dict[str, object]:
    event = ets.build_event(
        event_id=f"evt-github-pr-{repo.replace('/', '-')}-{pr_number}",
        tenant_id="lantern",
        workspace_id="github",
        evidence_id=f"github-pr-{repo}-{pr_number}",
        event_type="github.pr.evidence_recorded",
        subject_ref=f"github://{repo}/pull/{pr_number}",
        artifact_bytes=pr_summary_bytes,
        metadata={
            "repo": repo,
            "pr_number": pr_number,
            "commit_sha": commit_sha,
            "human_review_required": True,
            "claim_boundary": "ETS verifies PR evidence packet hash and proof material only, not code correctness.",
        },
        source_system="GitHub",
        actor_id="github-adapter",
        correlation_id=f"github-pr-{pr_number}",
    )
    result = ets.append_event(event)
    return {"append_result": result, "bundle": ets.get_bundle(str(result["event_id"]))}
```

## Batch ingestion pattern

Use batch ingestion when a system emits multiple related events. Keep each event independently hashable and appendable.

```python
from __future__ import annotations

from collections.abc import Iterable

from app.ets_client import ETSClient
from ets.core import EvidenceEvent


def append_many(ets: ETSClient, events: Iterable[EvidenceEvent]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for event in events:
        try:
            results.append(ets.append_event(event))
        except Exception as exc:
            results.append(
                {
                    "event_id": event.event_id,
                    "status": "failed",
                    "reason": str(exc),
                }
            )
    return results
```

## Audit replay pattern

Audit replay reconstructs whether a previously submitted event still verifies with supplied proof material.

```python
from __future__ import annotations

from ets.core import EvidenceProofBundle
from ets.core.proofs import verify_inclusion_proof
from ets.reports.certificate import create_certificate


def replay_bundle(bundle_json: dict[str, object]) -> dict[str, object]:
    bundle = EvidenceProofBundle.model_validate(bundle_json)
    result = verify_inclusion_proof(bundle.inclusion_proof)
    certificate = create_certificate(
        EvidenceProofBundle(
            event=bundle.event,
            event_hash=bundle.event_hash,
            leaf_hash=bundle.leaf_hash,
            tree_head=bundle.tree_head,
            inclusion_proof=bundle.inclusion_proof,
            verification_result=result,
        ),
        "markdown",
    )
    return {
        "valid": result.valid,
        "reason": result.reason,
        "event_id": bundle.event.event_id,
        "root_hash": result.root_hash,
        "certificate": certificate,
    }
```

## Tree-head progression and rollback suspicion

Use consistency proofs to demonstrate growth from one tree size to another. For production use, signed tree heads and independent anchoring should be reviewed by the deployment owner.

```python
from ets.core import InMemoryAppendOnlyLog, generate_consistency_proof
from ets.core.proofs import verify_consistency_proof

log = InMemoryAppendOnlyLog()
# append events first
# ...

proof = generate_consistency_proof(log.list_entries(), previous_tree_size=2)
result = verify_consistency_proof(proof)

if not result.valid:
    print("rollback or consistency suspicion", result.reason)
```

## Certificate wording by vertical

| Vertical | Certificate must not claim |
|---|---|
| AI governance | AI output correctness, fairness, safety, legal sufficiency, model alignment. |
| DevSecOps | Code safety, vulnerability absence, production readiness, supply-chain completeness. |
| Enterprise compliance | Control effectiveness, legal compliance, all expected evidence was submitted. |
| Healthcare | Medical correctness, consent legal sufficiency, raw PHI authenticity. |
| Insurance | Coverage correctness, actuarial fairness, claim truth, consumer-law compliance. |
| Finance | Legal materiality correctness, fraud truth, payment authorization validity. |
| Civic/election-adjacent | Election correctness, vote totals, ballot validity, official results, vote of record. |
| Emergency/sensor | Physical-world truth, sensor accuracy, responder correctness, completeness. |
| Legal/HR | Court admissibility, legal sufficiency, official chain of custody, employment-law conclusion. |
| Lantern internal | Infrastructure correctness, code correctness, customer entitlement, final business approval. |

## Production hardening checklist

Before any production deployment, complete these gates:

```text
[ ] Choose durable storage provider and backup plan.
[ ] Enable tenant/workspace scoping.
[ ] Define event taxonomy and metadata schema per vertical.
[ ] Define redaction profile per vertical.
[ ] Decide raw evidence storage boundary.
[ ] Add signed tree-head mode and key-management process.
[ ] Define external anchor strategy, if used.
[ ] Define certificate templates and non-claim boundaries.
[ ] Define policy-gated routing table.
[ ] Define human-review requirements.
[ ] Define retention and deletion policies.
[ ] Define incident response and break-glass handling.
[ ] Add monitoring for append failures, proof failures, auth failures, and storage validation errors.
[ ] Test replay from exported proof bundles.
[ ] Test root mismatch and tamper detection.
[ ] Test tenant isolation and 404 non-leak behavior.
[ ] Confirm no sensitive records are present in public fixtures or demos.
```

## End-to-end example: full vertical adapter

This example records an AI-assisted support recommendation, routes it through a policy gate, and generates a certificate.

```python
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.ets_client import ETSClient


@dataclass(frozen=True)
class SupportRecommendation:
    ticket_id: str
    recommendation_text: str
    model_name: str
    model_version: str
    reviewer_required: bool
    customer_visible: bool


def record_support_recommendation(
    ets: ETSClient,
    recommendation: SupportRecommendation,
) -> dict[str, object]:
    artifact_bytes = recommendation.recommendation_text.encode("utf-8")
    recommendation_hash = sha256(artifact_bytes).hexdigest()

    event = ets.build_event(
        event_id=f"evt-support-recommendation-{recommendation.ticket_id}",
        tenant_id="lantern",
        workspace_id="opshelm",
        evidence_id=f"support-recommendation-{recommendation.ticket_id}",
        event_type="opshelm.support_recommendation.generated",
        subject_ref=f"opshelm://tickets/{recommendation.ticket_id}/recommendation",
        artifact_bytes=artifact_bytes,
        metadata={
            "ticket_id": recommendation.ticket_id,
            "recommendation_hash": recommendation_hash,
            "model_name": recommendation.model_name,
            "model_version": recommendation.model_version,
            "reviewer_required": recommendation.reviewer_required,
            "customer_visible": recommendation.customer_visible,
            "raw_customer_data_excluded": True,
            "claim_boundary": "ETS verifies the support recommendation hash and proof material only, not technical correctness or customer entitlement.",
        },
        source_system="OpsHelm",
        actor_id="agent:opshelm",
        correlation_id=f"ticket-{recommendation.ticket_id}",
        redaction_profile="basic_pii",
    )

    append_result = ets.append_event(event)
    bundle = ets.get_bundle(str(append_result["event_id"]))
    certificate = ets.certificate(bundle, "markdown")
    proof_valid = bool(bundle["verification_result"]["valid"])

    route = route_evidence(
        proof_valid=proof_valid,
        requested_action="external_release" if recommendation.customer_visible else "archive",
        sensitivity="restricted" if recommendation.customer_visible else "internal",
        external_release=recommendation.customer_visible,
        civic_or_election_adjacent=False,
    )

    return {
        "append_result": append_result,
        "bundle": bundle,
        "certificate": certificate,
        "route": route,
    }
```

## Recommended repository additions for future passes

The next development passes should add:

```text
examples/verticals/ai_governance.py
examples/verticals/devsecops.py
examples/verticals/healthcare_hash_only.py
examples/verticals/insurance_claims.py
examples/verticals/finance_disclosure.py
examples/verticals/civic_boundary.py
examples/verticals/emergency_sensor.py
examples/verticals/legal_hr.py
examples/verticals/lantern_opshelm.py
```

Each example should use synthetic data only and should be backed by tests that verify:

```text
event schema validation
canonical hash determinism
append success
proof generation
proof verification
certificate claim-safety
policy routing
negative tamper case
```

## Summary

ETS should be implemented as a proof-bearing evidence operations layer. Across verticals, the implementation recipe is the same:

```text
hash raw artifact outside ETS
capture metadata as EvidenceEvent
append to ETS
verify proof
generate certificate
policy route
audit replay
preserve non-claim boundaries
```

The value of ETS is not that it magically proves reality. The value is that it makes submitted digital evidence reproducible, hash-bound, proof-bearing, certificate-readable, and policy-routable before humans or automation act on it.
