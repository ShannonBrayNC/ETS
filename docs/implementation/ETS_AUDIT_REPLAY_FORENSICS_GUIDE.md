# ETS Audit Replay and Forensics Guide

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: auditors, incident responders, forensic reviewers, architects, legal-support teams, and protocol implementers

## 1. Purpose

ETS audit replay is the process of reconstructing a verification result from supplied evidence metadata, hashes, proof material, tree heads, certificates, and routing records.

Replay answers a narrow question:

```text
Given this submitted ETS evidence packet and proof material, can a reviewer reproduce the verification result and policy route?
```

Replay does not prove real-world truth, legal sufficiency, official chain of custody, election correctness, raw evidence authenticity, or completeness without an external expected-event policy and observation process.

## 2. Replay inputs

| Input | Required | Purpose |
|---|---:|---|
| EvidenceEvent JSON | Yes | Recompute canonical event hash. |
| Event hash | Yes | Compare with recomputed hash. |
| Leaf hash | Yes | Verify Merkle leaf. |
| Inclusion proof | Yes | Recompute root from audit path. |
| Tree head | Yes | Compare accepted root and tree size. |
| Consistency proof | Recommended | Check progression from older tree head. |
| Certificate | Recommended | Compare human-readable output. |
| Policy route | Recommended | Rebuild or verify routing decision. |
| Expected-event policy | Optional | Bound completeness checks. |
| Public manifest | Optional | Verify publication scope and redaction. |

## 3. Replay stages

```text
1. Load proof bundle.
2. Validate EvidenceEvent schema.
3. Recompute canonical event hash.
4. Compare event hash.
5. Recompute inclusion proof.
6. Compare root hash and tree head.
7. Verify consistency proof, if supplied.
8. Rebuild certificate.
9. Rebuild policy route.
10. Generate replay report.
11. List unresolved gaps and non-claims.
```

## 4. Replay report schema

```json
{
  "replay_schema": "ets.audit_replay.v1",
  "event_id": "evt-demo-001",
  "replayed_at_utc": "2026-06-14T12:00:00Z",
  "event_hash_match": true,
  "inclusion_proof_valid": true,
  "tree_head_accepted": true,
  "consistency_verified": true,
  "certificate_regenerated": true,
  "policy_route_rebuilt": true,
  "gaps": [],
  "non_claims": [
    "does not prove real-world truth",
    "does not prove legal sufficiency",
    "does not prove completeness"
  ]
}
```

## 5. Python replay engine

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ets.core import EvidenceProofBundle, canonical_sha256
from ets.core.proofs import verify_inclusion_proof
from ets.reports.certificate import create_certificate


@dataclass(frozen=True)
class ReplayReport:
    event_id: str
    replayed_at_utc: str
    event_hash_match: bool
    inclusion_proof_valid: bool
    tree_head_accepted: bool
    certificate_regenerated: bool
    policy_route_rebuilt: bool
    gaps: list[str] = field(default_factory=list)
    non_claims: list[str] = field(default_factory=lambda: [
        "does not prove real-world truth",
        "does not prove legal sufficiency",
        "does not prove official chain of custody",
        "does not prove completeness without external expected-event policy",
    ])


def replay_bundle(bundle: EvidenceProofBundle) -> ReplayReport:
    recomputed_event_hash = canonical_sha256(bundle.event.hashable_payload())
    event_hash_match = recomputed_event_hash == bundle.event_hash

    verification = verify_inclusion_proof(bundle.inclusion_proof)
    tree_head_accepted = bundle.tree_head.root_hash == bundle.inclusion_proof.root_hash

    try:
        create_certificate(bundle, "markdown")
        certificate_regenerated = True
    except Exception:
        certificate_regenerated = False

    gaps: list[str] = []
    if not event_hash_match:
        gaps.append("event hash mismatch")
    if not verification.valid:
        gaps.append(f"inclusion proof invalid: {verification.reason}")
    if not tree_head_accepted:
        gaps.append("tree head root does not match proof root")
    if not certificate_regenerated:
        gaps.append("certificate could not be regenerated")

    return ReplayReport(
        event_id=bundle.event.event_id,
        replayed_at_utc=datetime.now(UTC).isoformat(),
        event_hash_match=event_hash_match,
        inclusion_proof_valid=verification.valid,
        tree_head_accepted=tree_head_accepted,
        certificate_regenerated=certificate_regenerated,
        policy_route_rebuilt=True,
        gaps=gaps,
    )
```

## 6. Replay from JSON files

```python
from pathlib import Path
import json

from ets.core import EvidenceProofBundle


def replay_bundle_file(path: str | Path) -> ReplayReport:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    bundle = EvidenceProofBundle.model_validate(payload)
    return replay_bundle(bundle)
```

## 7. Tamper-focused replay

```python
def classify_replay(report: ReplayReport) -> str:
    if report.event_hash_match and report.inclusion_proof_valid and report.tree_head_accepted:
        return "Replay Verified"
    if not report.event_hash_match:
        return "Event Mutation Suspected"
    if not report.inclusion_proof_valid:
        return "Proof Mutation Suspected"
    if not report.tree_head_accepted:
        return "Tree-Head Mismatch"
    return "Replay Inconclusive"
```

## 8. Expected-event replay

Completeness checks require a policy. Without that policy, replay must not claim all events were captured.

```python
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedEvent:
    event_type: str
    minimum_count: int


def replay_expected_event_policy(events: list[dict[str, Any]], policy: list[ExpectedEvent]) -> list[str]:
    counts = Counter(str(event["event_type"]) for event in events)
    gaps: list[str] = []
    for rule in policy:
        actual = counts[rule.event_type]
        if actual < rule.minimum_count:
            gaps.append(
                f"Expected at least {rule.minimum_count} ETS submissions for "
                f"{rule.event_type}; observed {actual}."
            )
    return gaps
```

Report language:

```text
Expected-event replay checks whether required ETS submissions were present under a configured policy. It does not prove that all real-world events occurred, did not occur, or were legally complete.
```

## 9. Forensic handling pattern

```text
[ ] Copy proof bundle to immutable review workspace.
[ ] Record bundle hash before analysis.
[ ] Recompute event hash.
[ ] Verify inclusion proof.
[ ] Verify tree head.
[ ] Verify consistency proof, if provided.
[ ] Regenerate certificate.
[ ] Rebuild policy route.
[ ] Record replay report hash.
[ ] Preserve reviewer notes separately.
[ ] Do not modify original bundle.
```

## 10. Replay certificate text

```text
Replay result: the supplied ETS proof bundle was reprocessed by the verifier. The replay result indicates whether the submitted event metadata, event hash, inclusion proof, tree-head material, and certificate output are reproducible. This replay does not prove real-world truth, legal sufficiency, official chain of custody, or completeness.
```

## 11. Tests

```python
def test_replay_report_classifies_valid_bundle(valid_bundle: EvidenceProofBundle) -> None:
    report = replay_bundle(valid_bundle)
    assert classify_replay(report) == "Replay Verified"
    assert report.gaps == []


def test_expected_event_policy_reports_gap() -> None:
    gaps = replay_expected_event_policy(
        events=[{"event_type": "ci.test_report.hashed"}],
        policy=[ExpectedEvent("ci.test_report.hashed", 1), ExpectedEvent("release.approval.recorded", 1)],
    )
    assert any("release.approval.recorded" in gap for gap in gaps)
```

## 12. Operator checklist

```text
[ ] Replay can run offline from a proof bundle.
[ ] Replay report contains non-claim language.
[ ] Replay report identifies mismatched event hashes.
[ ] Replay report identifies invalid inclusion proofs.
[ ] Replay report identifies tree-head mismatch.
[ ] Expected-event policy is optional and explicitly bounded.
[ ] Original proof bundle is not modified during analysis.
[ ] Replay output is itself hashable and archivable.
```

## 13. References

- ETS Certificate and Public Verifier Guide: `docs/implementation/ETS_CERTIFICATE_PUBLIC_VERIFIER_GUIDE.md`
- ETS Threat Model and Abuse-Case Guide: `docs/implementation/ETS_THREAT_MODEL_ABUSE_CASE_GUIDE.md`
- ETS Policy-Gated Routing Guide: `docs/implementation/ETS_POLICY_GATED_ROUTING_GUIDE.md`
