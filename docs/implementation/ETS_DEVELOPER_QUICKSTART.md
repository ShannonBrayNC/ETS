# ETS Developer Quickstart: 15-Minute Proof Pipeline

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: Python developers, architects, demo builders, reviewers, and integrators

## 1. Purpose

This guide gets a developer from a clean checkout to a working ETS proof pipeline:

```text
install -> run API -> create EvidenceEvent -> append -> prove -> verify -> bundle -> certificate -> policy route -> replay
```

ETS is the Evidence Transparency System. This quickstart demonstrates how ETS verifies submitted-event metadata, content hashes, inclusion proofs, tree-head material, verification certificates, and policy-routing records. It does not prove real-world truth, legal sufficiency, official chain of custody, election correctness, raw evidence authenticity, or completeness without an external expected-event policy and observation process.

All examples are fictional, local-only, and non-PII.

## 2. Public-safe rules before you run anything

Do not use live data in this quickstart.

Never paste these into examples, commits, issues, proof bundles, public manifests, or screenshots:

```text
secrets
API keys
tokens
private keys
certificates
real PII
real PHI/ePHI
production customer evidence
official election data
medical records
financial account records
legal records
restricted incident details
USPTO receipts
application numbers
claim charts
attorney-review notes
```

Use synthetic records only. The toy artifact in this guide is a fictional JSON object created in memory.

## 3. Prerequisites

Use Windows PowerShell 7+ and Python 3.12 or newer.

```powershell
py -3.12 --version
git --version
```

Clone and install:

```powershell
git clone https://github.com/ShannonBrayNC/ETS.git
Set-Location ETS
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run local checks before building on the protocol:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```

## 4. Start the ETS API and testing lab

Terminal 1, local API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

Terminal 2, Python testing lab UI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.lab.app:app --reload --port 8100
```

Open:

```text
http://localhost:8100/lab
```

Useful API endpoints:

```text
GET  /health
GET  /ready
GET  /version
GET  /api/v1/log/head
POST /api/v1/events
GET  /api/v1/events/{event_id}
GET  /api/v1/proofs/inclusion/{event_id}
GET  /api/v1/bundles/{event_id}
POST /api/v1/verify/inclusion
POST /reports/certificate
```

## 5. Create a one-file quickstart script

Create:

```powershell
New-Item -ItemType Directory -Force .\examples\quickstart | Out-Null
notepad .\examples\quickstart\quickstart_pipeline.py
```

Paste this script:

```python
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from ets.core import EvidenceEvent, InMemoryAppendOnlyLog, EvidenceProofBundle, SignedTreeHead
from ets.core import canonical_sha256, generate_inclusion_proof
from ets.core.proofs import verify_inclusion_proof
from ets.reports.certificate import create_certificate


BASE_URL = "http://localhost:8000"


def artifact_bytes() -> bytes:
    """Return a fictional local artifact.

    In a real deployment this might be a build report, approval record,
    sensor export, audit packet, or AI workflow output. For the quickstart
    it is synthetic and safe to print.
    """

    return b'{"fictional": true, "workflow": "quickstart", "result": "approved-for-demo"}'


def build_event(raw_bytes: bytes) -> EvidenceEvent:
    """Build the ETS EvidenceEvent metadata wrapper."""

    return EvidenceEvent(
        event_id="evt-quickstart-001",
        tenant_id="demo-tenant",
        workspace_id="quickstart",
        evidence_id="evidence-quickstart-001",
        event_type="workflow.evidence",
        subject_ref="fictional://quickstart/artifact-001",
        content_hash=sha256(raw_bytes).hexdigest(),
        content_hash_alg="sha256",
        metadata={
            "guide": "ETS Developer Quickstart",
            "classification": "public-safe-demo",
            "fictional": True,
            "review_required": False,
            "claim_boundary": "ETS verifies submitted metadata and proof material only.",
        },
        created_at_utc=datetime.now(UTC),
        source_system="quickstart-script",
        actor_id="developer-local",
        correlation_id="quickstart-run-001",
        external_refs={"artifact_uri": "fictional://quickstart/artifact-001"},
        redaction_profile="none",
    )


def run_local_python_pipeline(event: EvidenceEvent) -> dict[str, Any]:
    """Append, prove, verify, bundle, and certify without the API."""

    log = InMemoryAppendOnlyLog()
    entry = log.append(event)
    proof = generate_inclusion_proof(log.list_entries(), entry.log_index)
    verification = verify_inclusion_proof(proof)

    tree_head = SignedTreeHead(
        tree_size=proof.tree_size,
        root_hash=proof.root_hash,
        created_at_utc=datetime.now(UTC),
        log_id="quickstart-local-log",
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
        "entry": entry,
        "proof": proof,
        "verification": verification,
        "bundle": bundle,
        "certificate_markdown": create_certificate(bundle, "markdown"),
        "certificate_json": create_certificate(bundle, "json"),
    }


def append_event_api(event: EvidenceEvent) -> dict[str, Any]:
    response = httpx.post(
        f"{BASE_URL}/api/v1/events",
        json=event.model_dump(mode="json"),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def get_bundle_api(event_id: str) -> dict[str, Any]:
    response = httpx.get(f"{BASE_URL}/api/v1/bundles/{event_id}", timeout=15)
    response.raise_for_status()
    return response.json()


def certificate_api(bundle: dict[str, Any], output_format: str = "markdown") -> str:
    response = httpx.post(
        f"{BASE_URL}/reports/certificate",
        json={"bundle": bundle, "format": output_format},
        timeout=15,
    )
    response.raise_for_status()
    return str(response.json()["content"])


def route_after_verification(*, proof_valid: bool, sensitivity: str, external_release: bool) -> dict[str, str]:
    """Tiny policy-gate example for demo routing."""

    if not proof_valid:
        return {
            "decision": "Quarantine / Reject",
            "required_state": "Requires Human Review",
            "reason": "proof material is invalid or missing",
        }
    if sensitivity in {"confidential", "restricted", "regulated"} or external_release:
        return {
            "decision": "Human Review",
            "required_state": "Public Release Restricted",
            "reason": "verified evidence is sensitive or externally visible",
        }
    return {
        "decision": "Automation Approval",
        "required_state": "Hash Verified + Inclusion Proof Verified",
        "reason": "proof material verified and no sensitive release flag is present",
    }


def main() -> None:
    raw = artifact_bytes()
    event = build_event(raw)

    print("1. artifact_sha256", sha256(raw).hexdigest())
    print("2. canonical_event_sha256", canonical_sha256(event.hashable_payload()))

    local = run_local_python_pipeline(event)
    print("3. local_log_index", local["entry"].log_index)
    print("4. local_root_hash", local["proof"].root_hash)
    print("5. local_verification", local["verification"].valid, local["verification"].reason)

    routing = route_after_verification(
        proof_valid=bool(local["verification"].valid),
        sensitivity="public-demo",
        external_release=False,
    )
    print("6. route", routing)

    print("7. certificate preview")
    print("\n".join(local["certificate_markdown"].splitlines()[:12]))

    # API path. Requires uvicorn ets.api.app:app on port 8000.
    append_response = append_event_api(event)
    api_bundle = get_bundle_api(str(append_response["event_id"]))
    api_certificate = certificate_api(api_bundle, "markdown")
    print("8. api_event_id", append_response["event_id"])
    print("9. api_certificate_preview")
    print("\n".join(api_certificate.splitlines()[:12]))


if __name__ == "__main__":
    main()
```

Run it:

```powershell
.\.venv\Scripts\python.exe .\examples\quickstart\quickstart_pipeline.py
```

## 6. Expected output pattern

The exact hashes will vary when timestamps change, but the shape should look like this:

```text
1. artifact_sha256 <hex digest>
2. canonical_event_sha256 <hex digest>
3. local_log_index 0
4. local_root_hash <hex digest>
5. local_verification True proof verified
6. route {'decision': 'Automation Approval', ...}
7. certificate preview
8. api_event_id evt-quickstart-001
9. api_certificate_preview
```

If the API portion fails, check that the local API is running on port 8000.

## 7. What each step proves

| Step | What it proves | What it does not prove |
|---|---|---|
| Artifact hash | The bytes used in the demo map to a SHA-256 digest. | The real-world artifact is true, complete, lawful, or official. |
| EvidenceEvent | Metadata can be represented in the ETS event contract. | The source system was honest. |
| Canonical hash | Equivalent hashable payloads produce stable digests. | The event was externally observed. |
| Append-only log | The event was appended at a local log index. | The local log is globally available or production hardened. |
| Inclusion proof | The event belongs to the generated tree root. | The root is independently witnessed unless external anchoring/signing is enabled. |
| Certificate | A claim-safe receipt can be rendered. | The certificate is not legal acceptance, election correctness, or official custody. |
| Policy route | Verified evidence can be routed into a controlled action. | Automation should not bypass human review for sensitive or regulated evidence. |

## 8. Tamper test

Add this to the bottom of the script before `main()` returns:

```python
    tampered = local["proof"].model_copy(update={"root_hash": "0" * 64})
    tampered_verification = verify_inclusion_proof(tampered)
    print("10. tampered_verification", tampered_verification.valid, tampered_verification.reason)
```

Expected result:

```text
10. tampered_verification False computed root does not match proof root
```

That is the pocket lightning: the verifier recomputes the proof path and rejects the altered root.

## 9. Next implementation steps

After the quickstart works:

1. Replace the fictional artifact with a synthetic fixture from your vertical.
2. Add a tenant/workspace convention.
3. Add a redaction profile.
4. Add policy routes for public release, human review, quarantine, automation, and archive.
5. Enable SQLite for local durable testing.
6. Add JWT/JWKS auth before shared environments.
7. Add signed tree heads before claiming stronger trust-service properties.
8. Add external anchoring only after the deployment owner approves publication semantics.

## 10. Done criteria

You are done with the quickstart when you can demonstrate:

```text
[ ] API starts successfully.
[ ] Lab UI loads.
[ ] Fictional EvidenceEvent builds.
[ ] Event appends locally.
[ ] Inclusion proof verifies.
[ ] Certificate renders.
[ ] API event append works.
[ ] API proof bundle retrieval works.
[ ] API certificate generation works.
[ ] Tampered proof fails.
[ ] Public-safe claim boundary is preserved.
```
