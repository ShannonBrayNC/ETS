# ETS Threat Model and Abuse-Case Guide

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: security engineers, architects, auditors, reviewers, and maintainers

## 1. Purpose

ETS is an evidence transparency and verification layer. That makes the threat model different from a normal application threat model: the danger is not only that an attacker breaks the system, but that a reviewer believes a certificate proves more than it actually proves.

This guide identifies threats, abuse cases, controls, and tests for ETS implementations.

## 2. Core non-claim boundary

ETS verifies submitted-event metadata, content hashes, inclusion proofs, tree-head progression, verification certificates, policy-routing records, and replayable proof material.

ETS does not prove real-world truth, legal sufficiency, official chain of custody, election correctness, vote totals, ballot validity, raw evidence authenticity, model correctness, fairness, safety, or completeness without an external expected-event policy and observation process.

## 3. Assets to protect

| Asset | Why it matters |
|---|---|
| EvidenceEvent metadata | Defines what ETS believes was submitted. |
| Content hash | Links metadata to external raw artifacts. |
| Event hash | Canonical fingerprint of submitted event metadata. |
| Leaf hash | Merkle leaf used in proof computation. |
| Append-only log | Establishes ordering and inclusion. |
| Tree head | Summarizes a log state. |
| Signing key | Gives tree heads or releases stronger authenticity. |
| Proof bundle | Portable verification packet. |
| Certificate | Human-readable claim boundary and verification result. |
| Public manifest | External publication surface. |
| Tenant/workspace boundary | Prevents cross-tenant evidence leakage. |
| Expected-event policy | Defines what completeness means within a limited scope. |

## 4. Actor model

```text
honest integrator
curious public reviewer
source system operator
malicious source system
malicious tenant
compromised maintainer account
compromised signing key
external attacker
confused downstream automation
overclaiming marketer or reporter
```

The last two matter. ETS can be technically correct and still be misused if a certificate is interpreted as proof of truth, legality, or election correctness.

## 5. Abuse cases

| Abuse case | Example | Control |
|---|---|---|
| False metadata | Source system submits a misleading artifact description. | Source authorization, source identifiers, human review, external custody controls. |
| Omitted event | Required evidence is never submitted. | Expected-event policy, gap reports, manual observation. |
| Tampered event | Event JSON is edited after append. | Canonical hash recomputation fails. |
| Tampered proof | Root hash or audit path is changed. | Verifier recomputes path and rejects mismatch. |
| Stale tree head | Old accepted root is presented as latest. | Tree-head progression and freshness checks. |
| Fork/equivocation | Two conflicting tree heads exist for same log size. | Signed tree heads, witnessing, anchoring, monitor comparison. |
| Tenant bleed | Tenant A retrieves Tenant B bundle. | Tenant/workspace scoping and negative tests. |
| Sensitive public leak | Proof bundle exposes PII or restricted context. | Redaction profiles, public manifest review, release gates. |
| Certificate overclaim | Certificate says ETS proves truth or legality. | Claim-boundary tests and publication review. |
| Automation confusion | Valid proof triggers unsafe action. | Policy-gated routing and human review for sensitive events. |
| Dependency compromise | Build action injects bad code. | SSDF-aligned controls, pinned actions, Dependabot, code review. |

## 6. STRIDE-style mapping

| Threat family | ETS example | Mitigation |
|---|---|---|
| Spoofing | Fake source system submits evidence. | Authenticated source identity, source allowlists, signer identity. |
| Tampering | Proof bundle edited. | Recompute hashes and proof paths. |
| Repudiation | Operator denies publication or route decision. | Append routing events and certificate generation events. |
| Information disclosure | Public manifest leaks sensitive fields. | Redaction profiles and public-safe manifest schema. |
| Denial of service | API flooded with event submissions. | Rate limits, queueing, tenant quotas, resource limits. |
| Elevation of privilege | Tenant bypasses workspace scope. | Claim-scoped auth and negative access tests. |

## 7. Threat checks in Python

### 7.1 Proof mutation test

```python
from ets.core import InMemoryAppendOnlyLog, generate_inclusion_proof
from ets.core.proofs import verify_inclusion_proof


def assert_tampered_root_rejected(log: InMemoryAppendOnlyLog) -> None:
    entries = log.list_entries()
    proof = generate_inclusion_proof(entries, 0)
    tampered = proof.model_copy(update={"root_hash": "0" * 64})
    result = verify_inclusion_proof(tampered)
    assert result.valid is False
    assert result.reason == "computed root does not match proof root"
```

### 7.2 Event mutation test

```python
from copy import deepcopy

from ets.core import canonical_sha256


def assert_event_mutation_changes_hash(event_payload: dict[str, object]) -> None:
    original = canonical_sha256(event_payload)
    mutated = deepcopy(event_payload)
    mutated["metadata"] = {**dict(mutated.get("metadata", {})), "review_required": False}
    changed = canonical_sha256(mutated)
    assert changed != original
```

### 7.3 Certificate overclaim test

```python
BANNED_CERTIFICATE_PHRASES = (
    "proves real-world truth",
    "proves legal sufficiency",
    "proves election correctness",
    "proves vote totals",
    "proves ballot validity",
    "official chain of custody",
)


def assert_certificate_is_claim_safe(certificate_text: str) -> None:
    lowered = certificate_text.lower()
    for phrase in BANNED_CERTIFICATE_PHRASES:
        assert phrase not in lowered
    assert "does not prove" in lowered
```

### 7.4 Tenant isolation test pattern

```python
import httpx


def assert_cross_tenant_lookup_is_hidden(base_url: str, event_id: str) -> None:
    response = httpx.get(
        f"{base_url}/api/v1/events/{event_id}",
        headers={"X-ETS-Tenant": "wrong-tenant", "X-ETS-Workspace": "wrong-workspace"},
        timeout=15,
    )
    assert response.status_code == 404
```

## 8. Expected-event gap detection

ETS cannot prove completeness without a policy that says what should exist. This gap report stays bounded.

```python
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedEventRule:
    event_type: str
    minimum_count: int
    phase: str


def find_expected_event_gaps(events: list[dict[str, object]], rules: list[ExpectedEventRule]) -> list[str]:
    counts = Counter(str(event["event_type"]) for event in events)
    gaps: list[str] = []
    for rule in rules:
        actual = counts[rule.event_type]
        if actual < rule.minimum_count:
            gaps.append(
                f"missing expected ETS submissions for {rule.event_type}: "
                f"expected at least {rule.minimum_count}, observed {actual}"
            )
    return gaps
```

Safe language for gap reports:

```text
This gap report indicates whether expected records were submitted to ETS under the configured policy. It does not prove that unobserved real-world events did or did not occur, that all legally required records exist, or that any external outcome is correct.
```

## 9. Controls by implementation phase

| Phase | Required controls |
|---|---|
| Local demo | Synthetic data, no secrets, local-only API, unsigned tree heads allowed only with clear label. |
| Controlled validation | SQLite persistence, auth enabled, tenant/workspace scoping, redaction profile, CI tests. |
| Pre-production | Signed tree heads, backup/restore, key-management runbook, rate limits, monitoring. |
| Public verifier | Redacted manifests, certificate non-claims, tamper test endpoint, publication approval gate. |
| Production candidate | External witnessing/anchoring, incident playbook, rotation playbook, independent review. |

## 10. Operator checklist

```text
[ ] Threat model reviewed before public release.
[ ] Public manifests cannot include sensitive fields.
[ ] Certificates include non-claim language.
[ ] Invalid proof cannot route to automation.
[ ] Cross-tenant event lookup returns 404 or equivalent no-leak response.
[ ] Expected-event policy is separate from proof verification.
[ ] Key compromise response is documented.
[ ] Repository push protection and secret scanning are enabled.
[ ] Dependency update process is documented.
[ ] Public docs do not include private patent material.
```

## 11. References

- ETS Security Hardening Guide: `docs/implementation/ETS_SECURITY_HARDENING_GUIDE.md`
- ETS Policy-Gated Routing Guide: `docs/implementation/ETS_POLICY_GATED_ROUTING_GUIDE.md`
- OWASP API Security Top 10: `https://owasp.org/API-Security/`
- NIST Secure Software Development Framework: `https://csrc.nist.gov/pubs/sp/800/218/final`
- CISA Zero Trust Maturity Model: `https://www.cisa.gov/zero-trust-maturity-model`
