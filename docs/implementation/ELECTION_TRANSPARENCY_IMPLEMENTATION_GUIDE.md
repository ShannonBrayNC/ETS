# Building Transparency in Election Systems with ETS

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: election technologists, election officials, public-sector architects, auditors, security engineers, civic transparency builders, and ETS integrators

## 1. Purpose

This guide explains how to use ETS, the Evidence Transparency System, to build a transparency layer around election-adjacent evidence workflows without turning ETS into voting software, tabulation software, voter registration software, ballot-marking software, ballot-counting software, election correctness software, or the vote of record.

The goal is narrow and useful:

```text
Capture public-safe election process evidence.
Hash raw artifacts outside ETS.
Record minimal metadata as EvidenceEvent records.
Append those events to an ETS transparency log.
Generate inclusion proofs and verification certificates.
Publish sanitized proof bundles and public manifests.
Route sensitive or election-adjacent evidence through human review.
Replay the audit trail later without exposing voters, ballots, secrets, or restricted records.
```

ETS does **not** replace certified voting systems, statutory canvass processes, official records retention, risk-limiting audits, recounts, legal challenges, election authority decisions, or chain-of-custody procedures. It creates a verifiable evidence overlay for submitted artifacts and process records.

## 2. Public-safe claim boundary

ETS verifies:

- submitted-event metadata;
- content hashes;
- inclusion proofs;
- tree-head progression;
- verification certificates;
- policy-routing records;
- audit replay material supplied to ETS.

ETS does **not** prove:

- real-world truth;
- legal sufficiency;
- official chain of custody;
- election correctness;
- vote totals;
- ballot validity;
- voter eligibility;
- raw evidence authenticity;
- completeness without an external expected-event policy and observation process.

All examples in this guide use fictional, local-only, non-PII data.

## 3. Standards and research context

ETS should be implemented as a transparency and evidence-routing layer beside established election standards, not as a substitute for them.

| Area | Source | ETS implementation takeaway |
|---|---|---|
| VVSG 2.0 | The U.S. Election Assistance Commission describes VVSG as requirements against which voting systems can be tested, and VVSG 2.0 includes auditability and software-independence concepts. | ETS can help publish evidence that process artifacts were submitted, hashed, and verified, but ETS does not certify a voting system or validate election correctness. |
| Software independence and evidence-based elections | EAC/NIST E2E protocol evaluation materials describe VVSG 2.0 Principle 9 as requiring auditable systems and supporting evidence-based elections through software independence. | ETS can preserve public evidence packets, but independent audits still require voter-verifiable paper records, statutory procedures, and jurisdictional controls. |
| NIST voting common data formats | NIST has common data format work for Cast Vote Records, Election Results Reporting, and Election Event Logging implementation guidance. | ETS should hash CDF exports and record CDF metadata, version, jurisdiction scope, artifact hash, and publication policy. |
| Election infrastructure cybersecurity | NIST VTS 200-1 profiles cybersecurity risk management for election infrastructure, including voter registration, voting, and voting systems. | ETS evidence collection should be read-only, segmented, least-privilege, and governed by election infrastructure security controls. |
| Election security and chain of custody | EAC election security resources discuss locks, tamper-evident seals, cameras, testing before and after elections, audits, access controls, and chain-of-custody procedures for physical materials and voting systems. | ETS can record hashes and metadata for custody records, seal logs, transfer manifests, L&A artifacts, testing artifacts, and audit artifacts, but cannot replace physical custody. |
| End-to-end verifiability | EAC/NIST E2E work addresses protocols for cryptographically verifiable voting systems. | ETS can publish evidence around E2E artifacts or protocol outputs, but ETS does not become the E2E voting protocol unless separately designed, certified, and legally adopted. |

References for implementers:

- EAC VVSG overview: `https://www.eac.gov/voting-equipment/voluntary-voting-system-guidelines`
- EAC VVSG 2.0: `https://www.eac.gov/vvsg-20`
- EAC/NIST End-to-End Protocol Evaluation Process: `https://www.eac.gov/voting-equipment/end-end-e2e-protocol-evaluation-process`
- EAC election security clearinghouse: `https://www.eac.gov/election-officials/clearinghouse-resources-election-security`
- EAC election security preparedness: `https://www.eac.gov/election-officials/election-security-preparedness`
- NIST Cast Vote Records CDF: `https://www.nist.gov/publications/cast-vote-records-common-data-format-specification-version-10`
- NIST Election Results CDF: `https://www.nist.gov/publications/election-results-common-data-format-specification`
- NIST Implementation Guidance for Common Data Formats: `https://www.nist.gov/publications/implementation-guidance-common-data-formats`
- NIST Election Infrastructure Profile: `https://www.nist.gov/publications/cybersecurity-framework-election-infrastructure-profile`

## 4. The transparency model

ETS adds a transparency layer that is deliberately outside the official vote-capture and tabulation path.

```text
Official election process
  -> voting system, election management system, canvass, audit, statutory records

ETS evidence overlay
  -> hashes, metadata, proof bundles, certificates, public-safe manifests, replay records
```

ETS should receive only public-safe evidence metadata and hashes unless the deployment owner has a specific legal, security, and privacy-approved evidence storage model.

### 4.1 What to hash

Hash artifacts such as:

- voting system inventory export;
- certified software hash inventory;
- logic and accuracy test report;
- chain-of-custody transfer form;
- tamper-evident seal log;
- equipment check-in/check-out sheet;
- ballot container manifest;
- scanner batch summary;
- ballot accounting reconciliation worksheet;
- cast vote record export, when legally publishable or internally approved;
- election results CDF export;
- risk-limiting audit sample manifest;
- audit board report;
- incident log export;
- public meeting minutes;
- canvass packet index.

### 4.2 What not to store in ETS public examples

Never place these in public ETS examples, fixtures, manifests, issues, pull requests, or guides:

```text
voter names
voter registration records
signatures
driver license numbers
birth dates
addresses tied to individual voters
ballot images
raw ballots
secret ballot selections linked to voter-identifying data
non-public CVRs
pollbook extracts
system passwords
API keys
private keys
vendor credentials
network diagrams for live election systems
incident response details that reveal exploitable weaknesses
official election data unless explicitly released by the jurisdiction
USPTO receipts
application numbers
claim charts
attorney-review materials
```

### 4.3 Public evidence principle

The public packet should be able to say:

```text
The jurisdiction or demo system submitted artifact X.
Artifact X was represented by SHA-256 hash H.
ETS recorded metadata M at time T.
ETS appended the event at log index N.
The event has inclusion proof P against root R.
The certificate C verifies the supplied event and proof material.
The certificate does not prove election correctness, legal sufficiency, or completeness.
```

## 5. Election transparency event taxonomy

Use consistent event types so independent reviewers can reason about expected evidence.

| Phase | Event type | Purpose |
|---|---|---|
| Pre-election | `election.system_inventory.hashed` | Record hash of equipment inventory or certified component list. |
| Pre-election | `election.software_hash_inventory.hashed` | Record hash of certified software/hash inventory. |
| Pre-election | `election.logic_accuracy_test.completed` | Record L&A test report hash and witness metadata. |
| Pre-election | `election.seal_log.recorded` | Record hash of tamper-evident seal log. |
| Pre-election | `election.custody_transfer.recorded` | Record hash and metadata for transfer of materials/equipment. |
| Election day / voting period | `election.equipment_check.recorded` | Record check-in/check-out and status hash. |
| Election day / voting period | `election.incident_log.hashed` | Record public-safe incident log hash. |
| Post-election | `election.ballot_batch.accounted` | Record batch-level reconciliation artifact hash. |
| Post-election | `election.cvr_export.hashed` | Record CVR export hash and CDF metadata when approved. |
| Post-election | `election.results_report.hashed` | Record official or unofficial results artifact hash. |
| Audit | `election.audit_sample_manifest.hashed` | Record audit sample manifest hash. |
| Audit | `election.audit_report.hashed` | Record audit report hash and scope metadata. |
| Canvass | `election.canvass_packet.indexed` | Record canvass packet index hash. |
| Public transparency | `election.public_manifest.published` | Record sanitized public release manifest hash. |

## 6. Expected-event policy

ETS cannot prove completeness unless an expected-event policy defines what should have been submitted.

Create a policy per election, jurisdiction, contest scope, phase, or public demo.

```json
{
  "schema_version": "ets.election.expected_events.v1",
  "election_id": "fictional-2026-general-demo",
  "jurisdiction_id": "demo-county",
  "required_events": [
    {
      "event_type": "election.system_inventory.hashed",
      "minimum_count": 1,
      "phase": "pre_election",
      "public_release": true
    },
    {
      "event_type": "election.logic_accuracy_test.completed",
      "minimum_count": 1,
      "phase": "pre_election",
      "public_release": true
    },
    {
      "event_type": "election.ballot_batch.accounted",
      "minimum_count": 1,
      "phase": "post_election",
      "public_release": false
    },
    {
      "event_type": "election.results_report.hashed",
      "minimum_count": 1,
      "phase": "post_election",
      "public_release": true
    }
  ]
}
```

Completeness language must stay bounded:

```text
ETS can show whether required expected-event records were submitted to ETS under this policy. ETS cannot prove that unobserved real-world events did not occur, that all legally required records exist, or that the election outcome is correct.
```

## 7. Core data model

A public-safe election EvidenceEvent should contain metadata like this:

```json
{
  "schema_version": "ets.election.event.v1",
  "election_id": "fictional-2026-general-demo",
  "jurisdiction_id": "demo-county",
  "phase": "pre_election",
  "event_type": "election.logic_accuracy_test.completed",
  "artifact_type": "logic_accuracy_test_report",
  "artifact_hash_alg": "sha256",
  "artifact_hash": "hex string",
  "artifact_format": "pdf",
  "cdf_profile": null,
  "public_release": true,
  "witness_roles": ["election_official", "observer"],
  "device_scope": ["scanner-001"],
  "contest_scope": [],
  "batch_scope": [],
  "redaction_profile": "public_safe",
  "claim_boundary": "ETS verifies submitted L&A report hash and metadata only."
}
```

## 8. Core Python helper functions

The following examples assume the ETS project has been installed locally.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

### 8.1 Hash files without loading the whole file into memory

```python
from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hex digest for a local artifact.

    Use this for public-safe examples, L&A reports, seal-log exports,
    ballot-accounting summaries, public results files, and audit artifacts.
    Do not run this over private or restricted files unless the deployment
    owner has approved the evidence workflow.
    """

    digest = sha256()
    artifact_path = Path(path)
    with artifact_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

### 8.2 Build a public-safe ElectionEvidenceEvent factory

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Iterable

from ets.core import EvidenceEvent


@dataclass(frozen=True)
class ElectionTransparencyScope:
    election_id: str
    jurisdiction_id: str
    tenant_id: str
    workspace_id: str
    source_system: str = "ets-election-transparency-demo"


def _stable_scope_list(values: Iterable[str] | None) -> list[str]:
    return sorted(set(values or []))


def build_election_event(
    *,
    scope: ElectionTransparencyScope,
    event_id: str,
    evidence_id: str,
    event_type: str,
    phase: str,
    subject_ref: str,
    artifact_bytes: bytes,
    artifact_type: str,
    artifact_format: str,
    actor_id: str,
    correlation_id: str,
    public_release: bool,
    witness_roles: Iterable[str] | None = None,
    device_scope: Iterable[str] | None = None,
    contest_scope: Iterable[str] | None = None,
    batch_scope: Iterable[str] | None = None,
    cdf_profile: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> EvidenceEvent:
    """Create an ETS EvidenceEvent for election-adjacent transparency.

    artifact_bytes can be the bytes of a public-safe artifact or an already
    redacted export. For real election systems, prefer hashing the artifact in
    its approved storage location and sending only the hash and metadata.
    """

    artifact_hash = sha256(artifact_bytes).hexdigest()
    metadata: dict[str, Any] = {
        "schema_version": "ets.election.event.v1",
        "election_id": scope.election_id,
        "jurisdiction_id": scope.jurisdiction_id,
        "phase": phase,
        "artifact_type": artifact_type,
        "artifact_format": artifact_format,
        "artifact_hash_alg": "sha256",
        "artifact_hash": artifact_hash,
        "cdf_profile": cdf_profile,
        "public_release": public_release,
        "witness_roles": _stable_scope_list(witness_roles),
        "device_scope": _stable_scope_list(device_scope),
        "contest_scope": _stable_scope_list(contest_scope),
        "batch_scope": _stable_scope_list(batch_scope),
        "claim_boundary": (
            "ETS verifies submitted election-adjacent artifact hash, metadata, "
            "inclusion proof, tree-head material, and policy routing only. "
            "ETS does not prove election correctness, vote totals, ballot validity, "
            "legal sufficiency, official chain of custody, or completeness without "
            "external expected-event policy and observation."
        ),
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    return EvidenceEvent(
        event_id=event_id,
        tenant_id=scope.tenant_id,
        workspace_id=scope.workspace_id,
        evidence_id=evidence_id,
        event_type=event_type,
        subject_ref=subject_ref,
        content_hash=artifact_hash,
        content_hash_alg="sha256",
        metadata=metadata,
        created_at_utc=datetime.now(UTC),
        source_system=scope.source_system,
        actor_id=actor_id,
        correlation_id=correlation_id,
        external_refs={"subject_ref": subject_ref},
        redaction_profile="public_safe" if public_release else "restricted_review",
    )
```

### 8.3 Append and verify locally

```python
from __future__ import annotations

from datetime import UTC, datetime

from ets.core import EvidenceProofBundle, InMemoryAppendOnlyLog, SignedTreeHead
from ets.core import generate_inclusion_proof
from ets.core.proofs import verify_inclusion_proof
from ets.reports.certificate import create_certificate


scope = ElectionTransparencyScope(
    election_id="fictional-2026-general-demo",
    jurisdiction_id="demo-county",
    tenant_id="demo-election-office",
    workspace_id="public-transparency-demo",
)

logic_accuracy_event = build_election_event(
    scope=scope,
    event_id="evt-la-test-001",
    evidence_id="evidence-la-test-001",
    event_type="election.logic_accuracy_test.completed",
    phase="pre_election",
    subject_ref="fictional://demo-county/2026/la-test/report-001.pdf",
    artifact_bytes=b"fictional L&A test report bytes",
    artifact_type="logic_accuracy_test_report",
    artifact_format="pdf",
    actor_id="election-official-demo",
    correlation_id="pre-election-demo-001",
    public_release=True,
    witness_roles=["election_official", "observer"],
    device_scope=["scanner-001", "scanner-002"],
)

log = InMemoryAppendOnlyLog()
entry = log.append(logic_accuracy_event)
proof = generate_inclusion_proof(log.list_entries(), entry.log_index)
verification = verify_inclusion_proof(proof)
assert verification.valid, verification.reason

tree_head = SignedTreeHead(
    tree_size=proof.tree_size,
    root_hash=proof.root_hash,
    created_at_utc=datetime.now(UTC),
    log_id="ets-election-transparency-demo",
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

certificate_markdown = create_certificate(bundle, "markdown")
print(certificate_markdown)
```

### 8.4 Append through the ETS API

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from ets.core import EvidenceEvent


@dataclass(frozen=True)
class ETSApiClient:
    base_url: str = "http://localhost:8000"
    timeout_seconds: float = 15.0

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

    def create_certificate(self, bundle: dict[str, Any], output_format: str = "markdown") -> str:
        response = httpx.post(
            f"{self.base_url}/reports/certificate",
            json={"bundle": bundle, "format": output_format},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return str(response.json()["content"])


client = ETSApiClient()
append_result = client.append_event(logic_accuracy_event)
bundle_json = client.get_bundle(str(append_result["event_id"]))
certificate = client.create_certificate(bundle_json, "markdown")
print(certificate)
```

## 9. Vertical implementation patterns inside election transparency

### 9.1 Pre-election system inventory transparency

Purpose: record that an inventory artifact was submitted and hashed.

Do not publish live network details, internal credentials, equipment passwords, or non-public security details.

```python
def record_system_inventory(
    *,
    scope: ElectionTransparencyScope,
    inventory_json_bytes: bytes,
    actor_id: str,
    correlation_id: str,
) -> EvidenceEvent:
    return build_election_event(
        scope=scope,
        event_id=f"evt-system-inventory-{correlation_id}",
        evidence_id=f"evidence-system-inventory-{correlation_id}",
        event_type="election.system_inventory.hashed",
        phase="pre_election",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/inventory/system-inventory.json",
        artifact_bytes=inventory_json_bytes,
        artifact_type="system_inventory",
        artifact_format="json",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=True,
        extra_metadata={
            "inventory_scope": "public-safe equipment class and certification metadata only",
            "excluded_fields": ["network_address", "password", "credential", "private_key"],
        },
    )
```

### 9.2 Certified software hash inventory

Purpose: record a hash of a certified software/version inventory or trusted hash comparison result.

```python
def record_software_hash_inventory(
    *,
    scope: ElectionTransparencyScope,
    hash_inventory_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    device_scope: list[str],
) -> EvidenceEvent:
    return build_election_event(
        scope=scope,
        event_id=f"evt-software-hash-inventory-{correlation_id}",
        evidence_id=f"evidence-software-hash-inventory-{correlation_id}",
        event_type="election.software_hash_inventory.hashed",
        phase="pre_election",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/software/hash-inventory.json",
        artifact_bytes=hash_inventory_bytes,
        artifact_type="software_hash_inventory",
        artifact_format="json",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=True,
        device_scope=device_scope,
        extra_metadata={
            "comparison_type": "certified-hash-inventory",
            "claim_boundary": "ETS records submitted hash-inventory artifact proof only; certification authority remains external.",
        },
    )
```

### 9.3 Logic and accuracy test evidence

Purpose: record the report and witness metadata for logic and accuracy testing.

```python
def record_logic_accuracy_test(
    *,
    scope: ElectionTransparencyScope,
    report_pdf_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    device_scope: list[str],
    witness_roles: list[str],
) -> EvidenceEvent:
    return build_election_event(
        scope=scope,
        event_id=f"evt-la-test-{correlation_id}",
        evidence_id=f"evidence-la-test-{correlation_id}",
        event_type="election.logic_accuracy_test.completed",
        phase="pre_election",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/la/report.pdf",
        artifact_bytes=report_pdf_bytes,
        artifact_type="logic_accuracy_test_report",
        artifact_format="pdf",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=True,
        witness_roles=witness_roles,
        device_scope=device_scope,
        extra_metadata={
            "test_result": "fictional-pass",
            "expected_ballot_styles_tested": "recorded-in-source-artifact",
            "claim_boundary": "ETS verifies the submitted L&A artifact hash only; it does not certify the test was legally sufficient.",
        },
    )
```

### 9.4 Chain-of-custody transfer evidence

Purpose: record that a custody transfer document was submitted and hashed.

Do not publish signatures, personal phone numbers, private addresses, or sensitive facility details in public examples.

```python
def record_custody_transfer(
    *,
    scope: ElectionTransparencyScope,
    transfer_form_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    material_type: str,
    from_role: str,
    to_role: str,
    container_ids: list[str],
    seal_ids: list[str],
    public_release: bool = False,
) -> EvidenceEvent:
    return build_election_event(
        scope=scope,
        event_id=f"evt-custody-transfer-{correlation_id}",
        evidence_id=f"evidence-custody-transfer-{correlation_id}",
        event_type="election.custody_transfer.recorded",
        phase="custody",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/custody/{correlation_id}.pdf",
        artifact_bytes=transfer_form_bytes,
        artifact_type="chain_of_custody_transfer_form",
        artifact_format="pdf",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=public_release,
        extra_metadata={
            "material_type": material_type,
            "from_role": from_role,
            "to_role": to_role,
            "container_ids": sorted(container_ids),
            "seal_ids": sorted(seal_ids),
            "privacy_note": "public packet should redact signatures and sensitive facility details",
            "claim_boundary": "ETS does not replace physical custody controls or legal chain-of-custody requirements.",
        },
    )
```

### 9.5 Tamper-evident seal log

```python
def record_seal_log(
    *,
    scope: ElectionTransparencyScope,
    seal_log_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    seal_ids: list[str],
    container_ids: list[str],
    public_release: bool = True,
) -> EvidenceEvent:
    return build_election_event(
        scope=scope,
        event_id=f"evt-seal-log-{correlation_id}",
        evidence_id=f"evidence-seal-log-{correlation_id}",
        event_type="election.seal_log.recorded",
        phase="custody",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/custody/seal-log.json",
        artifact_bytes=seal_log_bytes,
        artifact_type="tamper_evident_seal_log",
        artifact_format="json",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=public_release,
        extra_metadata={
            "seal_ids": sorted(seal_ids),
            "container_ids": sorted(container_ids),
            "claim_boundary": "ETS records a submitted seal-log hash; physical inspection remains external.",
        },
    )
```

### 9.6 Ballot batch accounting

Purpose: hash ballot accounting worksheets or batch reconciliation summaries.

This is sensitive. Public release requires jurisdiction approval and redaction.

```python
def record_ballot_batch_accounting(
    *,
    scope: ElectionTransparencyScope,
    accounting_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    batch_id: str,
    precinct_id: str,
    ballot_count_reported: int,
    public_release: bool = False,
) -> EvidenceEvent:
    if ballot_count_reported < 0:
        raise ValueError("ballot_count_reported cannot be negative")

    return build_election_event(
        scope=scope,
        event_id=f"evt-ballot-batch-{batch_id}-{correlation_id}",
        evidence_id=f"evidence-ballot-batch-{batch_id}-{correlation_id}",
        event_type="election.ballot_batch.accounted",
        phase="post_election",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/batches/{batch_id}/accounting.json",
        artifact_bytes=accounting_bytes,
        artifact_type="ballot_batch_accounting_summary",
        artifact_format="json",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=public_release,
        batch_scope=[batch_id],
        extra_metadata={
            "batch_id": batch_id,
            "precinct_id": precinct_id,
            "ballot_count_reported": ballot_count_reported,
            "privacy_note": "do not include voter-identifying information or ballot selections",
            "claim_boundary": "ETS records batch-accounting artifact proof only; statutory reconciliation remains external.",
        },
    )
```

### 9.7 CVR export hash

Purpose: hash a cast vote record export when allowed by law and policy.

CVRs can be sensitive or public depending on jurisdiction, format, timing, and aggregation. ETS should default to metadata and hash only.

```python
def record_cvr_export_hash(
    *,
    scope: ElectionTransparencyScope,
    cvr_export_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    cdf_profile: str = "NIST SP 1500-103 CVR CDF",
    public_release: bool = False,
) -> EvidenceEvent:
    return build_election_event(
        scope=scope,
        event_id=f"evt-cvr-export-{correlation_id}",
        evidence_id=f"evidence-cvr-export-{correlation_id}",
        event_type="election.cvr_export.hashed",
        phase="post_election",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/exports/cvr.json",
        artifact_bytes=cvr_export_bytes,
        artifact_type="cast_vote_record_export",
        artifact_format="json",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=public_release,
        cdf_profile=cdf_profile,
        extra_metadata={
            "privacy_default": "hash-only",
            "do_not_include": ["voter identifiers", "ballot images", "non-public ballot selections"],
            "claim_boundary": "ETS verifies the submitted CVR export hash and metadata only; it does not validate voter intent or outcome correctness.",
        },
    )
```

### 9.8 Election results report hash

Purpose: record the hash of a results reporting file, public report, or NIST Election Results CDF export.

```python
def record_results_report_hash(
    *,
    scope: ElectionTransparencyScope,
    results_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    report_status: str,
    cdf_profile: str = "NIST SP 1500-100 Election Results CDF",
    public_release: bool = True,
) -> EvidenceEvent:
    allowed_status = {"unofficial", "canvass", "certified", "demo"}
    if report_status not in allowed_status:
        raise ValueError(f"report_status must be one of {sorted(allowed_status)}")

    return build_election_event(
        scope=scope,
        event_id=f"evt-results-report-{correlation_id}",
        evidence_id=f"evidence-results-report-{correlation_id}",
        event_type="election.results_report.hashed",
        phase="post_election",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/results/results.json",
        artifact_bytes=results_bytes,
        artifact_type="election_results_report",
        artifact_format="json",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=public_release,
        cdf_profile=cdf_profile,
        extra_metadata={
            "report_status": report_status,
            "claim_boundary": "ETS verifies the submitted results-report hash only; official results authority remains external.",
        },
    )
```

### 9.9 Audit sample manifest and audit report

Purpose: record audit sample selection artifacts and audit report artifacts.

```python
def record_audit_sample_manifest(
    *,
    scope: ElectionTransparencyScope,
    sample_manifest_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    audit_type: str,
    contest_scope: list[str],
    public_release: bool = True,
) -> EvidenceEvent:
    return build_election_event(
        scope=scope,
        event_id=f"evt-audit-sample-{correlation_id}",
        evidence_id=f"evidence-audit-sample-{correlation_id}",
        event_type="election.audit_sample_manifest.hashed",
        phase="audit",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/audit/sample-manifest.json",
        artifact_bytes=sample_manifest_bytes,
        artifact_type="audit_sample_manifest",
        artifact_format="json",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=public_release,
        contest_scope=contest_scope,
        extra_metadata={
            "audit_type": audit_type,
            "claim_boundary": "ETS records the audit artifact hash; statistical audit validity remains external.",
        },
    )


def record_audit_report(
    *,
    scope: ElectionTransparencyScope,
    audit_report_bytes: bytes,
    actor_id: str,
    correlation_id: str,
    audit_type: str,
    contest_scope: list[str],
    public_release: bool = True,
) -> EvidenceEvent:
    return build_election_event(
        scope=scope,
        event_id=f"evt-audit-report-{correlation_id}",
        evidence_id=f"evidence-audit-report-{correlation_id}",
        event_type="election.audit_report.hashed",
        phase="audit",
        subject_ref=f"fictional://{scope.jurisdiction_id}/{scope.election_id}/audit/report.pdf",
        artifact_bytes=audit_report_bytes,
        artifact_type="audit_report",
        artifact_format="pdf",
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=public_release,
        contest_scope=contest_scope,
        extra_metadata={
            "audit_type": audit_type,
            "claim_boundary": "ETS verifies the submitted audit report hash only; audit methodology and legal effect remain external.",
        },
    )
```

## 10. Policy routing for election transparency

Election-adjacent data needs conservative routing. A valid proof does not mean the artifact is safe to publish.

```python
from __future__ import annotations

from typing import Literal

ElectionDecision = Literal[
    "Publish Public Manifest",
    "Human Review",
    "Quarantine / Reject",
    "Archive Restricted",
]


def route_election_evidence(
    *,
    proof_valid: bool,
    public_release_requested: bool,
    contains_sensitive_scope: bool,
    election_adjacent: bool,
    official_record_claimed: bool,
    expected_event_policy_status: str,
) -> dict[str, str]:
    """Route election-adjacent evidence safely.

    expected_event_policy_status examples:
    - "not_checked"
    - "required_event_present"
    - "required_event_missing"
    - "unexpected_event"
    """

    if not proof_valid:
        return {
            "decision": "Quarantine / Reject",
            "required_state": "Requires Human Review",
            "reason": "proof material is invalid, missing, or root-mismatched",
        }

    if official_record_claimed:
        return {
            "decision": "Human Review",
            "required_state": "Official Authority Boundary Review",
            "reason": "public text must not imply ETS is the official record or certifies election results",
        }

    if expected_event_policy_status in {"required_event_missing", "unexpected_event"}:
        return {
            "decision": "Human Review",
            "required_state": "Expected Event Policy Review",
            "reason": "the event set does not match the configured expected-event policy",
        }

    if contains_sensitive_scope or not public_release_requested:
        return {
            "decision": "Archive Restricted",
            "required_state": "Restricted Evidence Archive",
            "reason": "verified proof material is not approved for public release",
        }

    if election_adjacent and public_release_requested:
        return {
            "decision": "Publish Public Manifest",
            "required_state": "Public-Safe Claim Boundary Included",
            "reason": "proof is valid, artifact is public-safe, and non-claim boundary is present",
        }

    return {
        "decision": "Human Review",
        "required_state": "General Review",
        "reason": "unclassified election transparency event",
    }
```

## 11. Public manifest generation

A public manifest should expose only event IDs, hashes, log positions, proof references, certificate references, and non-claim labels.

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class PublicManifestEntry:
    event_id: str
    event_type: str
    evidence_id: str
    artifact_hash: str
    artifact_hash_alg: str
    phase: str
    public_release: bool
    certificate_uri: str
    proof_bundle_uri: str


def build_public_manifest(
    *,
    election_id: str,
    jurisdiction_id: str,
    manifest_version: str,
    entries: list[PublicManifestEntry],
) -> dict[str, Any]:
    return {
        "schema_version": "ets.election.public_manifest.v1",
        "manifest_version": manifest_version,
        "election_id": election_id,
        "jurisdiction_id": jurisdiction_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "entries": [entry.__dict__ for entry in entries if entry.public_release],
        "claim_boundary": {
            "verifies": [
                "submitted-event metadata",
                "content hashes",
                "inclusion proofs",
                "tree-head material",
                "certificate references",
            ],
            "does_not_verify": [
                "real-world truth",
                "legal sufficiency",
                "official chain of custody",
                "election correctness",
                "vote totals",
                "ballot validity",
                "completeness without external expected-event policy",
            ],
            "not_voting_software": True,
            "not_tabulation_software": True,
            "not_vote_of_record": True,
        },
    }
```

## 12. Expected-event policy checker

```python
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class RequiredElectionEvent:
    event_type: str
    minimum_count: int
    phase: str
    public_release: bool


def check_expected_events(
    *,
    required: list[RequiredElectionEvent],
    observed_event_types: list[str],
) -> dict[str, object]:
    counts = Counter(observed_event_types)
    missing: list[dict[str, object]] = []

    for item in required:
        observed = counts[item.event_type]
        if observed < item.minimum_count:
            missing.append(
                {
                    "event_type": item.event_type,
                    "minimum_count": item.minimum_count,
                    "observed_count": observed,
                    "phase": item.phase,
                }
            )

    return {
        "valid_against_policy": not missing,
        "missing": missing,
        "observed_counts": dict(counts),
        "claim_boundary": (
            "This check only compares events submitted to ETS against the configured "
            "expected-event policy. It does not prove real-world completeness."
        ),
    }


required_events = [
    RequiredElectionEvent("election.system_inventory.hashed", 1, "pre_election", True),
    RequiredElectionEvent("election.logic_accuracy_test.completed", 1, "pre_election", True),
    RequiredElectionEvent("election.results_report.hashed", 1, "post_election", True),
]

policy_result = check_expected_events(
    required=required_events,
    observed_event_types=[
        "election.system_inventory.hashed",
        "election.logic_accuracy_test.completed",
    ],
)

assert policy_result["valid_against_policy"] is False
```

## 13. Public verifier example

The verifier consumes an ETS proof bundle and repeats the claim boundary.

```python
from __future__ import annotations

from typing import Any

import httpx


def verify_public_election_event(
    *,
    base_url: str,
    event_id: str,
) -> dict[str, Any]:
    bundle_response = httpx.get(f"{base_url}/api/v1/bundles/{event_id}", timeout=15)
    bundle_response.raise_for_status()
    bundle = bundle_response.json()

    certificate_response = httpx.post(
        f"{base_url}/reports/certificate",
        json={"bundle": bundle, "format": "json"},
        timeout=15,
    )
    certificate_response.raise_for_status()
    certificate = certificate_response.json()["content"]

    return {
        "event_id": event_id,
        "bundle": bundle,
        "certificate": certificate,
        "public_claim_boundary": (
            "This verifier checks ETS proof material only. It does not verify election correctness, "
            "vote totals, ballot validity, legal sufficiency, or official chain of custody."
        ),
    }
```

## 14. End-to-end demo assembly

This example creates multiple fictional election transparency events, appends them, verifies them, and builds a public manifest.

```python
from __future__ import annotations

from ets.core import InMemoryAppendOnlyLog, generate_inclusion_proof
from ets.core.proofs import verify_inclusion_proof


def run_election_transparency_demo() -> dict[str, object]:
    scope = ElectionTransparencyScope(
        election_id="fictional-2026-general-demo",
        jurisdiction_id="demo-county",
        tenant_id="demo-election-office",
        workspace_id="public-transparency-demo",
    )

    events = [
        record_system_inventory(
            scope=scope,
            inventory_json_bytes=b'{"inventory":"fictional public-safe inventory"}',
            actor_id="official-demo",
            correlation_id="001",
        ),
        record_logic_accuracy_test(
            scope=scope,
            report_pdf_bytes=b"fictional logic and accuracy test report",
            actor_id="official-demo",
            correlation_id="002",
            device_scope=["scanner-001"],
            witness_roles=["election_official", "observer"],
        ),
        record_results_report_hash(
            scope=scope,
            results_bytes=b'{"results":"fictional public results report"}',
            actor_id="official-demo",
            correlation_id="003",
            report_status="demo",
        ),
    ]

    log = InMemoryAppendOnlyLog()
    manifest_entries: list[PublicManifestEntry] = []

    for event in events:
        entry = log.append(event)
        proof = generate_inclusion_proof(log.list_entries(), entry.log_index)
        verification = verify_inclusion_proof(proof)
        assert verification.valid, verification.reason

        manifest_entries.append(
            PublicManifestEntry(
                event_id=event.event_id,
                event_type=event.event_type,
                evidence_id=event.evidence_id,
                artifact_hash=event.content_hash,
                artifact_hash_alg=event.content_hash_alg,
                phase=str(event.metadata["phase"]),
                public_release=bool(event.metadata["public_release"]),
                certificate_uri=f"fictional://certificates/{event.event_id}.json",
                proof_bundle_uri=f"fictional://proof-bundles/{event.event_id}.json",
            )
        )

    expected = check_expected_events(
        required=required_events,
        observed_event_types=[event.event_type for event in events],
    )

    public_manifest = build_public_manifest(
        election_id=scope.election_id,
        jurisdiction_id=scope.jurisdiction_id,
        manifest_version="demo-001",
        entries=manifest_entries,
    )

    return {
        "event_count": len(events),
        "expected_event_policy": expected,
        "public_manifest": public_manifest,
    }
```

## 15. API ingestion pattern for election offices

For a production-adjacent deployment, do not let election management systems push directly to a public ETS service. Use a staging collector:

```text
approved artifact export location
  -> read-only evidence collector
  -> hash + metadata builder
  -> restricted ETS ingest endpoint
  -> human review queue
  -> public-safe manifest publisher
```

Python ingestion runner:

```python
from __future__ import annotations

from pathlib import Path


def ingest_artifact_file(
    *,
    client: ETSApiClient,
    scope: ElectionTransparencyScope,
    path: Path,
    event_type: str,
    phase: str,
    artifact_type: str,
    artifact_format: str,
    actor_id: str,
    correlation_id: str,
    public_release: bool,
) -> dict[str, object]:
    artifact_bytes = path.read_bytes()
    event = build_election_event(
        scope=scope,
        event_id=f"evt-{event_type.replace('.', '-')}-{correlation_id}",
        evidence_id=f"evidence-{event_type.replace('.', '-')}-{correlation_id}",
        event_type=event_type,
        phase=phase,
        subject_ref=f"file://approved-export/{path.name}",
        artifact_bytes=artifact_bytes,
        artifact_type=artifact_type,
        artifact_format=artifact_format,
        actor_id=actor_id,
        correlation_id=correlation_id,
        public_release=public_release,
    )
    append_result = client.append_event(event)
    bundle = client.get_bundle(str(append_result["event_id"]))
    certificate = client.create_certificate(bundle, "markdown")
    routing = route_election_evidence(
        proof_valid=True,
        public_release_requested=public_release,
        contains_sensitive_scope=not public_release,
        election_adjacent=True,
        official_record_claimed=False,
        expected_event_policy_status="not_checked",
    )
    return {
        "append_result": append_result,
        "bundle": bundle,
        "certificate": certificate,
        "routing": routing,
    }
```

## 16. Security architecture

### 16.1 Collector constraints

The evidence collector should be:

- read-only against source artifact locations;
- isolated from vote-capture and tabulation systems;
- unable to modify official records;
- unable to access raw voter PII unless explicitly authorized;
- configured with least privilege;
- logged separately;
- operated by a role separate from official tabulation operations where possible;
- reviewed before public release.

### 16.2 Network pattern

```text
restricted election network or evidence export area
  -> one-way/manual export or controlled transfer
  -> evidence collector
  -> restricted ETS instance
  -> public-safe manifest after review
```

ETS should not create a new pathway into live election infrastructure.

### 16.3 Key management

Use local unsigned tree heads only for local demos. For production-adjacent pilots:

- sign tree heads;
- use separate signing keys per jurisdiction, environment, and election;
- protect signing keys in an approved key-management system;
- rotate keys under written procedure;
- publish public verification keys when appropriate;
- record key identifiers in certificates;
- never store private keys in the repo or public manifests.

### 16.4 Redaction and release tiers

| Tier | Meaning | Public release? |
|---|---|---|
| `public_safe` | Hashes, event IDs, artifact type, phase, public claim boundary. | Yes. |
| `restricted_review` | Internal metadata requiring review. | No public release by default. |
| `sensitive_custody` | Custody forms, signatures, facility details, sealed containers. | Restricted. |
| `statutory_record` | Records governed by law, retention, or official authority. | Only under jurisdiction policy. |
| `security_sensitive` | Network, vulnerability, credential, incident details. | Do not publish. |

## 17. Certificate language

Every public election-transparency certificate should include language like this:

```text
What this verifies:
- ETS received submitted metadata for the listed election-adjacent artifact.
- The submitted artifact was represented by the listed SHA-256 content hash.
- The event was included in the ETS log under the listed proof material.
- The verifier reproduced the inclusion proof result.

What this does not verify:
- ETS does not prove election correctness.
- ETS does not prove vote totals.
- ETS does not prove ballot validity.
- ETS does not prove voter eligibility.
- ETS does not replace official chain of custody.
- ETS does not replace statutory canvass, audit, recount, or certification procedures.
- ETS does not prove completeness without an external expected-event policy and observation process.
```

## 18. Test patterns

### 18.1 Test no voter PII fields in public manifest

```python
FORBIDDEN_PUBLIC_FIELDS = {
    "voter_name",
    "voter_id",
    "date_of_birth",
    "signature",
    "address",
    "driver_license",
    "ssn",
    "ballot_selection_linked_to_voter",
}


def assert_public_manifest_safe(manifest: dict[str, object]) -> None:
    serialized = repr(manifest).lower()
    for field in FORBIDDEN_PUBLIC_FIELDS:
        assert field not in serialized, f"forbidden public field leaked: {field}"
```

### 18.2 Test claim boundary is present

```python
def test_manifest_has_non_claim_boundary() -> None:
    manifest = build_public_manifest(
        election_id="fictional-2026-general-demo",
        jurisdiction_id="demo-county",
        manifest_version="test",
        entries=[],
    )
    boundary = manifest["claim_boundary"]
    assert "election correctness" in boundary["does_not_verify"]
    assert boundary["not_voting_software"] is True
    assert boundary["not_tabulation_software"] is True
    assert boundary["not_vote_of_record"] is True
```

### 18.3 Test expected-event policy detects missing evidence

```python
def test_expected_event_policy_detects_missing_results() -> None:
    result = check_expected_events(
        required=required_events,
        observed_event_types=[
            "election.system_inventory.hashed",
            "election.logic_accuracy_test.completed",
        ],
    )
    assert result["valid_against_policy"] is False
    assert result["missing"][0]["event_type"] == "election.results_report.hashed"
```

### 18.4 Test a public release is blocked when official-record language is claimed

```python
def test_official_record_claim_routes_to_human_review() -> None:
    route = route_election_evidence(
        proof_valid=True,
        public_release_requested=True,
        contains_sensitive_scope=False,
        election_adjacent=True,
        official_record_claimed=True,
        expected_event_policy_status="required_event_present",
    )
    assert route["decision"] == "Human Review"
    assert route["required_state"] == "Official Authority Boundary Review"
```

## 19. Operator checklist

Before using ETS for election transparency:

```text
[ ] Confirm jurisdiction authority and data release rules.
[ ] Define election_id and jurisdiction_id naming policy.
[ ] Define expected-event policy.
[ ] Define artifact types and event taxonomy.
[ ] Define redaction tiers.
[ ] Confirm ETS is outside vote capture and tabulation path.
[ ] Confirm read-only artifact export process.
[ ] Confirm no live credentials or private keys are published.
[ ] Confirm public certificates include non-claim boundaries.
[ ] Confirm chain-of-custody records are not exposed without approval.
[ ] Confirm CVR/result exports follow law, policy, and privacy review.
[ ] Confirm public manifest contains hashes and metadata only.
[ ] Confirm verifier can reproduce proof checks.
[ ] Confirm human review gate exists before public release.
[ ] Confirm incident/security-sensitive details are restricted.
[ ] Confirm the public repo contains no official election data or sensitive records.
```

## 20. Recommended rollout plan

### Phase 0: laboratory demo

Use fictional events only. Run `ets.lab` and the in-memory log.

### Phase 1: public-safe artifact hash demo

Hash fictional L&A reports, seal logs, and results files. Publish only manifest hashes and certificates.

### Phase 2: internal pilot with approved artifacts

Use restricted records in a non-public ETS deployment. Apply human review and redaction before publication.

### Phase 3: public manifest pilot

Publish a sanitized manifest with proof bundle references, non-claim labels, and verifier instructions.

### Phase 4: independent verifier pilot

Allow external reviewers to download proof bundles and reproduce ETS proof checks.

### Phase 5: governance integration

Align expected-event policies, release gates, retention rules, incident response, and audit workflows with jurisdiction procedures.

## 21. Public wording

Use:

```text
ETS provides a public-safe evidence transparency layer for submitted election-adjacent artifacts. It records hashes, metadata, inclusion proofs, certificates, and policy-routing records.
```

Use:

```text
ETS does not replace certified voting systems, official records, chain-of-custody procedures, statutory audits, recounts, canvass, or certification.
```

Do not use:

```text
ETS proves the election was correct.
ETS proves vote totals.
ETS proves ballots were valid.
ETS is a voting system.
ETS is tabulation software.
ETS is the official chain of custody.
ETS certifies election results.
ETS proves no evidence is missing unless no expected-event policy exists.
```

## 22. Summary

ETS can make election-adjacent processes more transparent by turning public-safe artifacts into verifiable evidence events. The useful pattern is not to place ETS inside voting or tabulation. The useful pattern is to surround election workflows with a restrained, verifiable, claim-safe evidence layer.

The design center is:

```text
secret ballots, public evidence boundaries, reproducible proof checks, human review, and no overclaims.
```

That is the lantern line: reveal the evidence path without pretending the lantern is the election itself.
