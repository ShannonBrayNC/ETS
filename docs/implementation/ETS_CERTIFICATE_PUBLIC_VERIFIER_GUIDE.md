# ETS Certificate and Public Verifier Guide

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: verifier builders, UX designers, auditors, integrators, security reviewers, and protocol implementers

## 1. Purpose

ETS certificates are claim-safe receipts for submitted evidence events and proof material. This guide explains how to build, render, verify, and publish certificates and public verifier experiences without overclaiming what ETS proves.

A certificate should answer:

```text
What was submitted?
What hash represents it?
Where was it included?
What proof verifies inclusion?
What tree head was used?
What verifier version checked it?
What policy route was assigned?
What does the result not prove?
```

A certificate must not say or imply that ETS proves real-world truth, legal sufficiency, official chain of custody, election correctness, vote totals, ballot validity, raw evidence authenticity, or completeness without an external expected-event policy and observation process.

## 2. Certificate roles

| Role | Description |
|---|---|
| JSON certificate | Machine-readable verification result for APIs, archives, and downstream tools. |
| Markdown certificate | Human-readable reviewer receipt for GitHub, reports, and handoffs. |
| HTML certificate | Browser-friendly rendering for demo portals and public verifier pages. |
| Public verifier | UI or CLI that recomputes proof material and displays a bounded result. |
| Proof bundle | Portable input containing event, event hash, leaf hash, tree head, inclusion proof, and verification result. |

## 3. Required certificate sections

Every ETS certificate should contain:

```text
certificate id or deterministic reference
generated_at_utc
verifier name and version
event id
evidence id
tenant/workspace when allowed
event type
content hash algorithm
content hash
event hash
leaf hash
tree size
leaf index
root hash
verification result
policy route
claim boundary
non-claim section
```

Sensitive deployments may omit tenant/workspace identifiers from public renderings while preserving them in private records.

## 4. Minimal certificate schema

```json
{
  "certificate_schema": "ets.certificate.v1",
  "generated_at_utc": "2026-06-14T12:00:00Z",
  "verifier": {
    "name": "ets-verifier",
    "version": "v0.1.0-alpha"
  },
  "event": {
    "event_id": "evt-demo-001",
    "evidence_id": "evidence-demo-001",
    "event_type": "workflow.evidence",
    "content_hash_alg": "sha256",
    "content_hash": "hex string",
    "event_hash": "hex string",
    "leaf_hash": "hex string"
  },
  "tree_head": {
    "log_id": "ets-demo-log",
    "tree_size": 1,
    "root_hash": "hex string",
    "signature_alg": null,
    "public_key_id": null
  },
  "proof": {
    "proof_type": "merkle_inclusion",
    "leaf_index": 0,
    "audit_path_length": 0
  },
  "verification": {
    "valid": true,
    "reason": "proof verified"
  },
  "policy": {
    "decision": "Human Review",
    "required_state": "Public Release Restricted",
    "reason": "verified evidence is externally visible"
  },
  "claim_boundary": "ETS verifies submitted-event metadata and proof material only."
}
```

## 5. Build a certificate from a local proof bundle

```python
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from ets.core import EvidenceEvent, EvidenceProofBundle, InMemoryAppendOnlyLog, SignedTreeHead
from ets.core import generate_inclusion_proof
from ets.core.proofs import verify_inclusion_proof
from ets.reports.certificate import create_certificate


def build_demo_bundle() -> EvidenceProofBundle:
    raw = b"fictional public verifier artifact"
    event = EvidenceEvent(
        event_id="evt-cert-demo-001",
        tenant_id="demo-tenant",
        workspace_id="public-verifier",
        evidence_id="evidence-cert-demo-001",
        event_type="workflow.evidence",
        subject_ref="fictional://public-verifier/artifact-001",
        content_hash=sha256(raw).hexdigest(),
        content_hash_alg="sha256",
        metadata={
            "fictional": True,
            "certificate_profile": "public_safe",
            "claim_boundary": "ETS verifies submitted metadata and proof material only.",
        },
        created_at_utc=datetime.now(UTC),
        source_system="certificate-guide",
        actor_id="developer-local",
        correlation_id="certificate-demo-001",
        external_refs={"artifact_uri": "fictional://public-verifier/artifact-001"},
        redaction_profile="none",
    )

    log = InMemoryAppendOnlyLog()
    entry = log.append(event)
    proof = generate_inclusion_proof(log.list_entries(), entry.log_index)
    verification = verify_inclusion_proof(proof)

    tree_head = SignedTreeHead(
        tree_size=proof.tree_size,
        root_hash=proof.root_hash,
        created_at_utc=datetime.now(UTC),
        log_id="certificate-guide-log",
        signature_alg=None,
        signature=None,
        public_key_id=None,
    )

    return EvidenceProofBundle(
        event=entry.event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=tree_head,
        inclusion_proof=proof,
        verification_result=verification,
    )


bundle = build_demo_bundle()
print(create_certificate(bundle, "markdown"))
print(create_certificate(bundle, "html"))
print(create_certificate(bundle, "json"))
```

## 6. Verify before rendering

Never render a green certificate from unverified proof material.

```python
from __future__ import annotations

from ets.core import EvidenceProofBundle
from ets.core.proofs import verify_inclusion_proof


def require_valid_bundle(bundle: EvidenceProofBundle) -> None:
    verification = verify_inclusion_proof(bundle.inclusion_proof)
    if not verification.valid:
        raise ValueError(f"invalid proof bundle: {verification.reason}")
    if verification.reason != bundle.verification_result.reason:
        raise ValueError("bundle verification result is stale or inconsistent")
```

## 7. Public verifier API pattern

The public verifier should accept a proof bundle, recompute verification, and return a bounded result.

```python
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ets.core import EvidenceProofBundle
from ets.core.proofs import verify_inclusion_proof
from ets.reports.certificate import create_certificate


class PublicVerifyRequest(BaseModel):
    bundle: dict[str, Any]
    format: str = "markdown"


app = FastAPI(title="ETS Public Verifier")


@app.post("/verify")
def verify_public_bundle(request: PublicVerifyRequest) -> dict[str, Any]:
    try:
        bundle = EvidenceProofBundle.model_validate(request.bundle)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid proof bundle shape") from exc

    verification = verify_inclusion_proof(bundle.inclusion_proof)
    if not verification.valid:
        return {
            "status": "rejected",
            "valid": False,
            "reason": verification.reason,
            "claim_boundary": CLAIM_BOUNDARY,
        }

    refreshed_bundle = bundle.model_copy(update={"verification_result": verification})
    certificate = create_certificate(refreshed_bundle, request.format)
    return {
        "status": "verified",
        "valid": True,
        "reason": verification.reason,
        "certificate": certificate,
        "claim_boundary": CLAIM_BOUNDARY,
    }


CLAIM_BOUNDARY = (
    "ETS verifies submitted-event metadata, content hashes, inclusion proofs, "
    "tree-head material, verifier output, and policy-routing records. It does "
    "not prove real-world truth, legal sufficiency, official chain of custody, "
    "election correctness, raw evidence authenticity, or completeness without "
    "an external expected-event policy and observation process."
)
```

## 8. Public verifier UX states

Use plain, bounded UI states.

| State | Label | Meaning | Color guidance |
|---|---|---|---|
| Verified | `Proof verified` | The submitted proof recomputed successfully. | Green only for proof status, not truth. |
| Rejected | `Proof rejected` | The proof failed verification. | Red. |
| Incomplete | `Missing proof material` | Required fields are missing. | Amber. |
| Under review | `Human review required` | Sensitive or public-impacting evidence needs review. | Amber. |
| Restricted | `Public release restricted` | Record should not be public. | Amber/red. |

Do not use labels like:

```text
Truth verified
Election verified
Legally valid
Official chain of custody proven
Fraud disproven
Votes certified
```

## 9. HTML certificate rendering rules

The HTML certificate should:

```text
[ ] show the verification result near the top
[ ] show event id, event type, and evidence id
[ ] show content hash and event hash
[ ] show tree size, leaf index, and root hash
[ ] show verifier version
[ ] show policy route
[ ] show non-claims above any public action button
[ ] avoid raw sensitive evidence
[ ] avoid application numbers, claim charts, or private IP records
```

Example safe HTML wrapper:

```python
def wrap_certificate_html(certificate_html: str) -> str:
    boundary = """
    <section class="claim-boundary">
      <h2>Claim boundary</h2>
      <p>This certificate verifies submitted-event metadata, hashes, inclusion proofs,
      tree-head material, verifier output, and policy-routing records. It does not prove
      real-world truth, legal sufficiency, official chain of custody, election correctness,
      raw evidence authenticity, or completeness without an external expected-event policy
      and observation process.</p>
    </section>
    """
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <title>ETS Verification Certificate</title>
    </head>
    <body>
      {boundary}
      <main>{certificate_html}</main>
    </body>
    </html>
    """
```

## 10. Offline verifier script

Create `verify_bundle_offline.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from ets.core import EvidenceProofBundle
from ets.core.proofs import verify_inclusion_proof
from ets.reports.certificate import create_certificate


def verify_bundle_file(path: str | Path, certificate_format: str = "markdown") -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    bundle = EvidenceProofBundle.model_validate(data)
    verification = verify_inclusion_proof(bundle.inclusion_proof)

    if not verification.valid:
        print("REJECTED")
        print(verification.reason)
        return 2

    refreshed = bundle.model_copy(update={"verification_result": verification})
    print("VERIFIED")
    print(create_certificate(refreshed, certificate_format))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(verify_bundle_file(sys.argv[1]))
```

Run:

```powershell
.\.venv\Scripts\python.exe .\verify_bundle_offline.py .\proof-bundle.json
```

## 11. Tamper failure demo

Use this in demos to show the verifier is not decorative.

```python
from ets.core.proofs import verify_inclusion_proof


def tamper_bundle_root(bundle: EvidenceProofBundle) -> EvidenceProofBundle:
    tampered_proof = bundle.inclusion_proof.model_copy(update={"root_hash": "0" * 64})
    return bundle.model_copy(update={"inclusion_proof": tampered_proof})


tampered = tamper_bundle_root(bundle)
result = verify_inclusion_proof(tampered.inclusion_proof)
assert result.valid is False
print(result.reason)
```

Expected result:

```text
computed root does not match proof root
```

## 12. Public manifest pattern

A public manifest should be a list of approved certificate summaries, not a data lake.

```json
{
  "schema_version": "ets.public_manifest.v1",
  "manifest_id": "manifest-demo-001",
  "generated_at_utc": "2026-06-14T12:00:00Z",
  "records": [
    {
      "event_id": "evt-demo-001",
      "event_type": "workflow.evidence",
      "content_hash_alg": "sha256",
      "content_hash": "hex string",
      "root_hash": "hex string",
      "tree_size": 1,
      "certificate_uri": "https://example.invalid/certificates/evt-demo-001.html",
      "proof_bundle_uri": "https://example.invalid/bundles/evt-demo-001.json",
      "public_release": true,
      "claim_boundary": "ETS verifies submitted proof material only."
    }
  ]
}
```

Manifest review checklist:

```text
[ ] no raw evidence
[ ] no secrets
[ ] no private identities
[ ] no restricted incident details
[ ] no official election data unless released by the jurisdiction
[ ] certificate link works
[ ] proof bundle link works
[ ] proof bundle verifies offline
[ ] non-claim language is visible
```

## 13. Policy routes for certificates

```python
from __future__ import annotations


def certificate_publication_route(
    *,
    proof_valid: bool,
    sensitivity: str,
    civic_or_election_adjacent: bool,
    requested_publication: bool,
) -> dict[str, str]:
    if not proof_valid:
        return {"decision": "Do Not Publish", "reason": "proof material failed verification"}
    if civic_or_election_adjacent:
        return {"decision": "Human Review", "reason": "civic/election-adjacent certificate requires non-claim review"}
    if sensitivity in {"restricted", "regulated", "confidential"}:
        return {"decision": "Human Review", "reason": "sensitive evidence cannot be auto-published"}
    if requested_publication:
        return {"decision": "Publish Certificate", "reason": "verified public-safe certificate"}
    return {"decision": "Archive", "reason": "verified certificate retained for replay"}
```

## 14. Certificate tests

Add tests like these to prevent regressions:

```python
def test_certificate_contains_non_claims() -> None:
    bundle = build_demo_bundle()
    markdown = create_certificate(bundle, "markdown")
    assert "does not" in markdown.lower()
    assert "real-world" in markdown.lower() or "real world" in markdown.lower()
    assert "legal" in markdown.lower()


def test_tampered_certificate_input_rejected() -> None:
    bundle = build_demo_bundle()
    tampered = tamper_bundle_root(bundle)
    result = verify_inclusion_proof(tampered.inclusion_proof)
    assert result.valid is False
```

## 15. Done criteria

A public verifier is ready for review when:

```text
[ ] accepts proof bundle JSON
[ ] validates bundle shape
[ ] recomputes inclusion proof
[ ] rejects tampered roots
[ ] renders JSON, Markdown, or HTML certificates
[ ] shows claim boundary in the UI
[ ] does not expose raw sensitive evidence
[ ] distinguishes proof verification from truth/legal/election claims
[ ] supports offline verification
[ ] has tests for valid, invalid, missing, and tampered bundles
```

## 16. Recommended next steps

1. Add sample synthetic proof bundles to a `samples/public-verifier` folder.
2. Add an offline verifier CLI test.
3. Add UI screenshots after the Explorer/public verifier panel stabilizes.
4. Add a public manifest signing profile after key management is reviewed.
5. Add an interop appendix for SCITT, Sigstore/Rekor, C2PA, and W3C PROV boundaries.
