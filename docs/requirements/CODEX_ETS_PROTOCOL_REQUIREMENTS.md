# Codex Requirements — Formal ETS Protocol Implementation

## 1. Purpose

This document defines public-safe implementation requirements for turning ETS
from a research concept into a formal, testable protocol and reference
implementation.

ETS is the **Evidence Transparency System**. It must evolve into an open protocol
and implementation for transforming digital assertions into verifiable evidence
artifacts.

The implementation must support:

- formal protocol specification;
- canonical evidence objects;
- deterministic canonicalization;
- cryptographic hashing and signing integration;
- append-only transparency logs;
- Merkle inclusion proofs;
- log consistency proof verification where implemented;
- verification APIs;
- CLI and SDK verifier tooling;
- conformance test vectors;
- security and privacy controls;
- Apache 2.0 release readiness;
- public patent-pending notice and private IP-boundary controls.

> Important: This document is technical planning only and is not legal advice.
> Private patent filings, claim charts, USPTO receipts, prior-art matrices, and
> attorney-review materials must remain outside the public repository.

---

## 2. Public Release and IP Boundary Workflow

Before a public release, the repository must contain only public-safe technical
implementation, protocol, demo, research, and release materials.

Requirements:

1. Keep private IP records in a separate non-public repository or counsel-managed
   workspace.
2. Publish only restrained patent-pending notice language through
   `PATENT_NOTICE.md`.
3. Exclude application numbers, confirmation numbers, USPTO receipts, payment
   records, provisional drafts, candidate claims, claim charts, prior-art
   matrices, attorney notes, and assignment strategy from the public repository.
4. Use synthetic or fictional evidence fixtures only.
5. Preserve claim-boundary language in README, release notes, demos, and reports.
6. Finalize public Apache 2.0 posture only after release readiness gates pass.

Deliverables:

- `PATENT_NOTICE.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `.github/dependabot.yml`
- `.github/pull_request_template.md`
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/security_boundary.md`
- `docs/release/PUBLIC_RELEASE_CHECKLIST.md`
- `docs/release/ALPHA_RELEASE_GATE.md`

Acceptance Criteria:

- Required public release guardrails exist.
- No private IP artifacts exist under public repository paths.
- No secrets, private keys, sensitive personal data, official election data, or
  restricted evidence are included.
- Public language does not claim patent allowance, claim scope, legal strategy,
  freedom to operate, real-world truth, legal sufficiency, election correctness,
  or completeness without external policy and observation.

---

## 3. Repository Structure Requirements

Codex must create or align the repository around this public structure:

```text
/docs
  /architecture
  /demo
  /governance
  /operations
  /release
  /reports
  /requirements
  /research
  /security
  /spec

/ets
  /api
  /core
  /demos
  /explorer-ui
  /reports
  /sdk
  /spec
  /verifier

/formal
  /alloy
  /apalache
  /lean
  /tla

/scripts
/tests
```

Acceptance Criteria:

- Structure exists or equivalent current structure is documented.
- README links to the protocol spec and release gates.
- All public-facing docs consistently refer to ETS as **Evidence Transparency
  System**.
- No public path is used as a private patent archive.

---

## 4. Formal Protocol Specification Requirements

The protocol documentation must define:

- protocol goals and non-goals;
- terminology;
- evidence lifecycle;
- EvidenceEvent object requirements;
- canonicalization requirements;
- hashing requirements;
- signature and key metadata requirements;
- transparency log behavior;
- proof formats;
- verification workflow;
- error model;
- conformance levels;
- security considerations;
- privacy considerations;
- public claim boundaries.

Acceptance Criteria:

- Clear normative language using `MUST`, `SHOULD`, and `MAY`.
- Protocol can be implemented by a third party without reading private material.
- Every required behavior maps to a test case or release-tracked gap.

---

## 5. Evidence Object Requirements

Each evidence event MUST support stable metadata sufficient for deterministic
hashing and verification. At minimum, the public protocol must define:

- schema version;
- event identifier;
- tenant/workspace scope where applicable;
- event type;
- event time;
- source system;
- content hash or hash-only evidence reference;
- metadata object;
- policy context where applicable;
- previous event or tree context where applicable.

Acceptance Criteria:

- JSON schema exists.
- Valid fixtures pass validation.
- Invalid fixtures fail validation with clear errors.
- Schema versioning behavior is documented.

---

## 6. Canonicalization Requirements

Requirements:

- Use deterministic JSON canonicalization.
- Object keys MUST be sorted.
- Insignificant whitespace MUST be removed.
- Unicode handling MUST be deterministic.
- Numeric representation rules MUST be documented.
- Field exclusion rules for hash calculation MUST be deterministic.

Test Requirements:

- Same semantic object with different key order produces same canonical output.
- Whitespace differences do not affect hash.
- Nested object key ordering is deterministic.
- Arrays preserve order.
- Hash field exclusion works exactly as specified.

---

## 7. Hashing, Logs, and Proof Requirements

The implementation must support:

- SHA-256 event and leaf hashing for v0.1;
- append-only log behavior;
- monotonic sequence numbers;
- Merkle root calculation;
- inclusion proof generation;
- inclusion proof verification;
- consistency proof verification where implemented;
- proof bundles that can be verified without raw evidence bytes.

ETS does not claim novelty in SHA-256, Merkle trees, Ed25519, generic
transparency logs, or generic policy engines.

---

## 8. Verification API and CLI Requirements

The API and CLI must support:

- local health/version/readiness checks;
- event append;
- event lookup;
- log head retrieval;
- inclusion proof retrieval;
- proof bundle retrieval;
- inclusion verification;
- consistency verification where implemented;
- certificate generation from supplied proof material.

The CLI must exit non-zero on invalid verification and must produce structured
failure reasons suitable for tests and automation.

---

## 9. Security, Privacy, and Evidence Boundary Requirements

ETS must preserve these boundaries:

- raw evidence bytes are outside the default ETS storage boundary;
- public fixtures are synthetic or fictional;
- secrets and credentials are never committed;
- real PII, production customer evidence, official election data, legal records,
  medical records, financial records, and restricted incident data are forbidden
  in public issues, demos, fixtures, and pull requests;
- verification certificates must be claim-safe and must not state unsupported
  legal or factual conclusions.

---

## 10. Release Readiness Requirements

Before public release:

```powershell
.\scripts\verify-ets-release-readiness.ps1
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ets-verify.exe --version
```

GitHub repository settings must also be verified manually or by an admin-capable
automation:

- secret scanning enabled;
- push protection enabled;
- Dependabot alerts enabled;
- Dependabot security updates enabled;
- CodeQL/default code scanning enabled;
- dependency graph enabled;
- `main` protected;
- pull requests required before merge;
- required status checks enabled;
- branch freshness required;
- force pushes blocked;
- branch deletion blocked.

---

## 11. Public Non-Claims

Public ETS materials must not say or imply that ETS proves:

- real-world truth;
- raw evidence authenticity;
- evidence completeness without an external expected-event policy and
  independent observation process;
- legal sufficiency;
- regulatory acceptance;
- election correctness;
- vote totals, ballot validity, official results, or vote of record;
- production trust-service readiness;
- patent allowance, claim scope, legal strategy, or freedom to operate.
