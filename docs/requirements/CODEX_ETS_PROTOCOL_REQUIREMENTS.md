# Codex Requirements — Formal ETS Protocol Implementation

## 1. Purpose

This document defines the Codex-ready implementation requirements for turning ETS from a research concept into a formal, testable protocol and reference implementation.

ETS must evolve into an open protocol and implementation for transforming digital assertions into verifiable evidence.

The implementation must support:

- Formal protocol specification
- Canonical evidence objects
- Deterministic canonicalization
- Cryptographic hashing and signing
- Append-only transparency logs
- Merkle inclusion proofs
- Log consistency proofs
- Verification APIs
- CLI and SDK verifier tooling
- Conformance test vectors
- Security and privacy controls
- Apache 2.0 release readiness
- Patent disclosure support materials

> Important: This document is technical planning only and is not legal advice. Patent strategy and final licensing decisions must be reviewed by qualified IP counsel before public release of patent-sensitive material.

---

## 2. Strategic Requirements

### 2.1 Patent-First, Publish-Second Workflow

Before releasing a polished protocol or production-quality implementation publicly, prepare patent disclosure material.

Requirements:

1. Create an internal invention disclosure document.
2. Capture novel protocol claims and differentiators.
3. Include system diagrams and protocol flows.
4. Identify prior art comparison areas.
5. Prepare provisional patent package with counsel.
6. Only after filing approval, finalize public Apache 2.0 release posture.

Deliverables:

- `docs/ip/INVENTION_DISCLOSURE_DRAFT.md`
- `docs/ip/PATENT_CLAIMS_CANDIDATES.md`
- `docs/ip/PRIOR_ART_REVIEW_AREAS.md`
- `docs/ip/PUBLIC_RELEASE_CHECKLIST.md`

Acceptance Criteria:

- Documents exist.
- Documents clearly distinguish protocol novelty from common primitives such as hashing, Merkle trees, logs, signatures, and blockchain anchoring.
- Documents contain attorney-review warnings.
- No secrets, private keys, or sensitive personal data are included.

---

## 3. Repository Structure Requirements

Codex must create or align the repository around this structure:

```text
/docs
  /book
  /requirements
  /spec
    ETS_PROTOCOL.md
    EVIDENCE_OBJECT.md
    CANONICALIZATION.md
    HASHING_AND_SIGNATURES.md
    TRANSPARENCY_LOG.md
    PROOFS.md
    VERIFICATION_API.md
    CONFORMANCE.md
  /ip
    INVENTION_DISCLOSURE_DRAFT.md
    PATENT_CLAIMS_CANDIDATES.md
    PRIOR_ART_REVIEW_AREAS.md
    PUBLIC_RELEASE_CHECKLIST.md
  /security
    THREAT_MODEL.md
    KEY_MANAGEMENT.md
    PRIVACY_MODEL.md
  /talks
    LIBERTARIAN_KEYNOTE.md
    TED_STYLE_TALK.md

/src
  /ets
    /core
    /api
    /verifier
    /cli
    /sdk
    /storage
    /schemas
    /tests

/tests
  /unit
  /integration
  /conformance
  /security
  /fixtures

/examples
  /ticketing
  /ai-decision
  /transaction
  /governance
```

Acceptance Criteria:

- Structure exists or equivalent current structure is documented.
- README links to the protocol spec, manuscript, and requirements.
- All public-facing docs consistently refer to ETS as `Evidence Transparency System` unless the project owner intentionally chooses `Evidence Trust System`.

---

## 4. Formal Protocol Specification Requirements

### 4.1 ETS Protocol v0.1

Create `docs/spec/ETS_PROTOCOL.md`.

Must define:

- Protocol goals
- Non-goals
- Terminology
- Evidence lifecycle
- Evidence object requirements
- Canonicalization requirements
- Hashing requirements
- Signature requirements
- Transparency log behavior
- Proof formats
- Verification workflow
- Error model
- Conformance levels
- Security considerations
- Privacy considerations

Acceptance Criteria:

- Clear normative language using `MUST`, `SHOULD`, and `MAY`.
- Protocol can be implemented by a third party without reading the book manuscript.
- Every required behavior maps to a test case.

---

## 5. Evidence Object Requirements

Create `docs/spec/EVIDENCE_OBJECT.md` and implementation schema under `src/ets/schemas`.

### 5.1 Required Fields

Each evidence object MUST support:

```json
{
  "schemaVersion": "ets.evidence.v0.1",
  "eventId": "uuid",
  "correlationId": "string",
  "sequence": 1,
  "timestamp": "RFC3339 UTC timestamp",
  "actor": {
    "type": "user|service|system|agent|external",
    "id": "string",
    "displayName": "optional string"
  },
  "action": "string",
  "eventType": "state_change|decision|observation|command|verification",
  "inputs": {},
  "outputs": {},
  "context": {
    "system": "string",
    "environment": "dev|test|stage|prod",
    "policyVersion": "optional string",
    "modelVersion": "optional string",
    "source": "optional string"
  },
  "previousHash": "optional string",
  "hashAlgorithm": "SHA-256",
  "hash": "string",
  "signature": {
    "algorithm": "optional string",
    "keyId": "optional string",
    "value": "optional string"
  }
}
```

### 5.2 Validation Rules

- `eventId` MUST be unique.
- `timestamp` MUST be RFC3339 UTC.
- `schemaVersion` MUST be present.
- `hashAlgorithm` MUST be explicit.
- `inputs`, `outputs`, and `context` MUST be valid JSON objects.
- `hash` MUST be computed over canonicalized evidence excluding the `hash` and `signature.value` fields unless the spec defines otherwise.

Acceptance Criteria:

- JSON schema exists.
- Valid fixture passes validation.
- Invalid fixtures fail validation with clear errors.
- Schema versioning behavior is documented.

---

## 6. Canonicalization Requirements

Create `docs/spec/CANONICALIZATION.md` and implementation in `src/ets/core`.

Requirements:

- Use deterministic JSON canonicalization.
- Object keys MUST be sorted.
- Insignificant whitespace MUST be removed.
- Unicode handling MUST be deterministic.
- Numeric representation rules MUST be documented.
- Field exclusion rules for hash calculation MUST be deterministic.

Preferred standard:

- RFC 8785 JSON Canonicalization Scheme where practical.

Functions required:

```text
canonicalizeEvidence(evidence) -> canonical_string
prepareEvidenceForHash(evidence) -> canonical_hash_input
```

Test Requirements:

- Same semantic object with different key order produces same canonical output.
- Whitespace differences do not affect hash.
- Nested object key ordering is deterministic.
- Arrays preserve order.
- Hash field exclusion works exactly as specified.
- Signature field exclusion works exactly as specified.

Acceptance Criteria:

- Unit tests cover at least 15 canonicalization cases.
- Test vectors are stored in `tests/fixtures/canonicalization`.

---

## 7. Hashing Requirements

Create `docs/spec/HASHING_AND_SIGNATURES.md` and implementation in `src/ets/core`.

Required functions:

```text
hashEvidence(evidence) -> hash_result
verifyEvidenceHash(evidence) -> verification_result
linkEvidence(previousEvidence, currentEvidence) -> linked_evidence
```

Requirements:

- SHA-256 MUST be supported for v0.1.
- Hash output MUST be lowercase hex unless otherwise specified.
- Hash calculation MUST use canonicalized evidence.
- Evidence hash verification MUST be deterministic.
- Broken hash verification MUST return clear failure reason.

Test Requirements:

- Known vector produces known SHA-256 output.
- Modified field causes verification failure.
- Modified nested field causes verification failure.
- Previous hash chain mismatch is detected.
- Missing required hash fails validation.

Acceptance Criteria:

- Unit tests cover success and failure paths.
- Test vectors can be used by external implementers.

---

## 8. Digital Signature Requirements

Requirements:

- v0.1 MAY support signatures, but the spec MUST define planned behavior.
- If implemented, support Ed25519 or ECDSA P-256.
- Signature metadata MUST include algorithm and key ID.
- Signature verification MUST be independent from evidence hash verification.

Required functions if implemented:

```text
signEvidence(evidence, privateKeyRef) -> signed_evidence
verifyEvidenceSignature(evidence, publicKey) -> signature_result
```

Test Requirements:

- Valid signature passes.
- Modified evidence fails signature verification.
- Wrong public key fails.
- Missing key ID produces explicit warning or failure.

Missing Item Added:

- Add key rotation and key compromise model under `docs/security/KEY_MANAGEMENT.md`.

---

## 9. Transparency Log Requirements

Create `docs/spec/TRANSPARENCY_LOG.md` and implementation under `src/ets/storage`.

### 9.1 Required Behavior

The transparency log MUST:

- Be append-only.
- Assign monotonic sequence numbers.
- Store evidence hashes.
- Support retrieval by event ID.
- Support retrieval by sequence.
- Support Merkle root calculation.
- Support signed tree heads in future versions.

Required functions:

```text
appendEvidence(evidence) -> append_result
getEvidence(eventId) -> evidence_record
getEvidenceBySequence(sequence) -> evidence_record
getLogRoot() -> log_root
getLogSize() -> integer
```

Test Requirements:

- Appending increases log size.
- Existing records cannot be overwritten.
- Duplicate event IDs are rejected or versioned according to spec.
- Sequence numbers are monotonic.
- Restart/persistence behavior is tested.

Acceptance Criteria:

- In-memory implementation exists for tests.
- File-backed or SQLite-backed implementation exists for local demos.
- Append-only behavior is enforced by tests.

---

## 10. Merkle Proof Requirements

Create `docs/spec/PROOFS.md` and implementation under `src/ets/core`.

Required proof types:

1. Inclusion proof
2. Consistency proof, if feasible for v0.1

Required functions:

```text
buildMerkleTree(hashes) -> tree
getMerkleRoot(tree) -> root_hash
createInclusionProof(eventHash, tree) -> inclusion_proof
verifyInclusionProof(eventHash, proof, rootHash) -> proof_result
createConsistencyProof(oldTreeSize, newTreeSize) -> consistency_proof
verifyConsistencyProof(oldRoot, newRoot, proof) -> proof_result
```

Test Requirements:

- Single-leaf tree works.
- Even number of leaves works.
- Odd number of leaves works.
- Inclusion proof passes for valid leaf.
- Inclusion proof fails for modified leaf.
- Inclusion proof fails for wrong root.
- Large tree test uses at least 1,000 leaves.

Acceptance Criteria:

- Proof format is documented.
- Proof fixtures are checked in.
- Verification does not require access to the full log.

---

## 11. Verification API Requirements

Create `docs/spec/VERIFICATION_API.md` and implementation under `src/ets/api`.

Required endpoints:

```text
POST /evidence
GET  /evidence/{eventId}
GET  /log/root
GET  /log/size
GET  /proof/inclusion/{eventId}
POST /verify/evidence
POST /verify/proof/inclusion
GET  /health
```

Optional endpoints:

```text
GET  /proof/consistency?fromSize=&toSize=
POST /verify/proof/consistency
```

API Requirements:

- JSON request and response bodies.
- Deterministic error codes.
- No stack traces in API responses.
- OpenAPI specification generated or maintained.
- API validates evidence before append.

Test Requirements:

- Endpoint tests for success cases.
- Endpoint tests for validation failure.
- Endpoint tests for tampered evidence.
- Endpoint tests for unknown event ID.
- Health endpoint test.
- OpenAPI document validation.

Acceptance Criteria:

- Integration tests can run locally.
- API test suite is included in CI.

---

## 12. CLI Verifier Requirements

Create implementation under `src/ets/cli`.

Required commands:

```text
ets verify evidence --file evidence.json
ets verify inclusion --file proof.json --root <rootHash>
ets hash evidence --file evidence.json
ets log root --source <path-or-url>
ets evidence append --file evidence.json
```

Test Requirements:

- CLI exits 0 on valid verification.
- CLI exits non-zero on invalid verification.
- CLI emits machine-readable JSON with `--json`.
- CLI emits human-readable output by default.

Acceptance Criteria:

- CLI has help text.
- CLI tests cover all commands.

---

## 13. SDK Requirements

Create SDK functions under `src/ets/sdk`.

Required SDK surface:

```text
createEvidence(input) -> evidence
hashEvidence(evidence) -> hash
verifyEvidence(evidence) -> result
appendEvidence(client, evidence) -> appendResult
getInclusionProof(client, eventId) -> proof
verifyInclusionProof(proof) -> result
```

Acceptance Criteria:

- SDK has examples.
- SDK has unit tests.
- SDK avoids leaking implementation internals.

---

## 14. Conformance Requirements

Create `docs/spec/CONFORMANCE.md`.

Conformance levels:

### ETS-L0: Structured Evidence
- Evidence schema validation only.

### ETS-L1: Integrity Evidence
- Canonicalization and hashing.

### ETS-L2: Append-Only Evidence Log
- Evidence can be appended and retrieved immutably.

### ETS-L3: Verifiable Transparency Log
- Inclusion proofs and root verification.

### ETS-L4: Independent Verification
- External verifier can validate evidence and proofs without privileged access.

### ETS-L5: Evidence-Driven Operations
- Critical workflows consume verification results operationally.

Test Requirements:

- Create conformance fixtures for L0-L4.
- Add command to run conformance suite.
- Document expected pass/fail outputs.

Acceptance Criteria:

- Third-party implementer can validate compatibility using fixtures.

---

## 15. Security Requirements

Create `docs/security/THREAT_MODEL.md`.

Threats to cover:

- Evidence tampering
- Record deletion
- Log forking
- Selective disclosure
- Replay attacks
- Signature key compromise
- Insider manipulation
- Missing-event attacks
- API abuse
- Denial of service
- Privacy leakage through metadata

Controls to document and implement where feasible:

- Hash verification
- Append-only enforcement
- Merkle proof validation
- Key rotation plan
- Authentication for write endpoints
- Rate limiting plan
- Audit logging of verifier access
- Redaction and minimization guidance

Test Requirements:

- Tampering tests.
- Replay tests where applicable.
- Invalid proof tests.
- Unauthorized append tests if auth is implemented.
- Fuzz-style malformed JSON tests.

Missing Item Added:

- Define missing-event detection strategies. ETS must eventually detect absence of expected evidence, not only tampering with captured evidence.

---

## 16. Privacy Requirements

Create `docs/security/PRIVACY_MODEL.md`.

Requirements:

- Separate content from proof.
- Support hashed references to sensitive data.
- Avoid storing raw secrets or PII in test fixtures.
- Define redaction model.
- Define public, restricted, and internal evidence views.
- Document GDPR/right-to-erasure tension and mitigation through data separation.

Test Requirements:

- Fixtures must not include real PII.
- Redacted evidence must still verify when designed to do so.
- Hash-only public proof flow must be tested.

---

## 17. Licensing Requirements

Required files:

- `LICENSE` using Apache License 2.0 after approval.
- `NOTICE` if needed.
- `docs/ip/PUBLIC_RELEASE_CHECKLIST.md`.

Requirements:

- Confirm license before broad public release.
- Include patent-grant implications in checklist.
- Ensure third-party dependencies are license-compatible.

Test / Validation:

- Add dependency license scan if package ecosystem supports it.
- Add CI check for missing license headers if headers are adopted.

Missing Item Added:

- Add release gate: no public protocol release tagged `v0.1` until IP counsel has reviewed patent/disclosure posture.

---

## 18. Documentation Requirements

Required docs:

- Protocol specification
- Developer quickstart
- Architecture overview
- API documentation
- CLI documentation
- Conformance guide
- Security model
- Privacy model
- Patent disclosure draft
- Public release checklist

README updates:

- Link to manuscript.
- Link to protocol docs.
- Explain current maturity level.
- Explain how to run tests.
- Explain how to run demo.

Acceptance Criteria:

- A non-author developer can clone, run tests, and understand protocol purpose within 15 minutes.

---

## 19. Demo Requirements

Create examples for:

### 19.1 Ticketing Demo

- Create ticket event.
- Add status update.
- Add resolution event.
- Verify ticket evidence chain.

### 19.2 AI Decision Demo

- Record prompt/input.
- Record model metadata.
- Record output.
- Verify decision evidence.

### 19.3 Transaction Demo

- Append transaction event.
- Generate inclusion proof.
- Verify proof.

### 19.4 Governance Demo

- Record public decision event.
- Expose public hash and proof.
- Keep sensitive content private.

Acceptance Criteria:

- Each demo has a README.
- Each demo has testable fixture output.
- Each demo can run without external secrets.

---

## 20. Testing Requirements

### 20.1 Unit Tests

Required coverage:

- Schema validation
- Canonicalization
- Hashing
- Hash verification
- Chain linking
- Merkle root generation
- Inclusion proof creation
- Inclusion proof verification
- Signature functions if implemented

### 20.2 Integration Tests

Required coverage:

- Append evidence through API.
- Retrieve evidence.
- Generate proof.
- Verify proof.
- Tamper evidence and confirm failure.

### 20.3 Conformance Tests

Required coverage:

- Known canonicalization vectors.
- Known hash vectors.
- Known Merkle proof vectors.
- Known invalid vectors.

### 20.4 Security Tests

Required coverage:

- Malformed JSON.
- Overlarge payload.
- Missing required fields.
- Invalid timestamps.
- Duplicate IDs.
- Tampered previous hash.
- Invalid proof path.

### 20.5 Regression Tests

Required behavior:

- Every bug fix gets a test.
- Fixtures are versioned.
- Protocol changes require fixture updates.

Acceptance Criteria:

- `npm test`, `pytest`, or equivalent project command runs all tests.
- CI blocks merge on failing tests.
- Coverage threshold should start at 80 percent for core protocol modules.

---

## 21. CI/CD Requirements

Create GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

Required jobs:

- Install dependencies
- Run lint
- Run unit tests
- Run integration tests
- Run conformance tests
- Validate docs links if practical
- Validate OpenAPI spec if present

Optional jobs:

- Dependency license scan
- Security scan
- Coverage upload

Acceptance Criteria:

- CI runs on pull request and push to main.
- Failed tests block merge if branch protection is enabled.

---

## 22. Missing Critical Items Added

The following items were missing or under-specified and must be included:

1. Formal protocol specification with normative language.
2. Conformance levels and test vectors.
3. Canonicalization standard and deterministic hash input rules.
4. Explicit evidence schema versioning.
5. Clear distinction between evidence, proof, and raw data.
6. Key management and signature rotation plan.
7. Missing-event detection strategy.
8. Privacy model separating content from proof.
9. Public release checklist tied to patent review.
10. API error model.
11. CLI verifier for independent validation.
12. Demo scenarios for ticketing, AI decisions, transactions, and governance.
13. CI gate for tests and specs.
14. Security threat model.
15. Third-party implementer conformance suite.
16. README correction decision: `Evidence Transparency System` vs `Evidence Trust System`.
17. Apache 2.0 license readiness checklist.
18. OpenAPI documentation for verification endpoints.
19. Human-readable verification reports.
20. Evidence retention and archival model.

---

## 23. Codex Execution Plan

### Sprint 1 — Protocol Skeleton and Repository Alignment

Tasks:

- Create docs/spec files.
- Create docs/security files.
- Create docs/ip files.
- Update README links.
- Decide and standardize project name expansion.

Tests:

- Markdown lint if available.
- Link validation if available.

Acceptance:

- Documentation skeleton committed.
- README points to protocol and manuscript.

### Sprint 2 — Evidence Schema and Canonicalization

Tasks:

- Implement evidence schema.
- Implement canonicalization.
- Implement validation.
- Add fixtures.

Tests:

- Schema tests.
- Canonicalization tests.
- Invalid fixture tests.

Acceptance:

- Deterministic canonical output proven by tests.

### Sprint 3 — Hashing and Evidence Chaining

Tasks:

- Implement hashEvidence.
- Implement verifyEvidenceHash.
- Implement linkEvidence.
- Add known vectors.

Tests:

- Hash success/failure.
- Mutation detection.
- Previous hash mismatch.

Acceptance:

- Core integrity tests pass.

### Sprint 4 — Transparency Log

Tasks:

- Implement append-only log.
- Implement sequence numbers.
- Implement retrieval.
- Implement root hash.

Tests:

- Append behavior.
- Duplicate handling.
- Persistence behavior.
- No overwrite behavior.

Acceptance:

- Append-only semantics enforced.

### Sprint 5 — Merkle Proofs

Tasks:

- Implement Merkle tree.
- Implement inclusion proof.
- Implement inclusion proof verification.
- Begin consistency proof design.

Tests:

- Single/even/odd/large tree.
- Valid and invalid proofs.

Acceptance:

- Inclusion proofs work without full log access.

### Sprint 6 — Verification API

Tasks:

- Implement API endpoints.
- Add OpenAPI spec.
- Add error model.

Tests:

- API integration tests.
- Tampered evidence tests.
- Unknown event tests.

Acceptance:

- API can ingest, prove, and verify evidence.

### Sprint 7 — CLI and SDK

Tasks:

- Implement CLI commands.
- Implement SDK facade.
- Add examples.

Tests:

- CLI return codes.
- JSON output mode.
- SDK unit tests.

Acceptance:

- Independent local verification works from CLI.

### Sprint 8 — Conformance Suite and Demos

Tasks:

- Add conformance fixtures.
- Add demos.
- Add demo READMEs.

Tests:

- Conformance suite.
- Demo execution tests.

Acceptance:

- Third-party compatibility can be tested.

### Sprint 9 — Security, Privacy, and Release Readiness

Tasks:

- Complete threat model.
- Complete privacy model.
- Complete public release checklist.
- Add license/dependency checks.

Tests:

- Malformed input tests.
- Privacy fixture checks.
- CI validation.

Acceptance:

- Repo is ready for attorney review and controlled public release.

---

## 24. Definition of Done

The ETS protocol implementation is considered v0.1 complete when:

- Protocol docs exist and use normative language.
- Evidence schema is implemented and tested.
- Canonicalization is deterministic and tested.
- Hashing and chain verification are implemented and tested.
- Append-only log exists and is tested.
- Inclusion proofs exist and are tested.
- Verification API exists and is tested.
- CLI verifier exists and is tested.
- Conformance fixtures exist.
- Security and privacy models exist.
- README is updated.
- CI runs all tests.
- Public release checklist is complete.
- Patent/IP counsel review gate is documented.

---

## 25. Codex Prompt Seed

Use this prompt when starting Codex work:

```text
You are working in the ShannonBrayNC/ETS repository. Implement the ETS formal protocol reference implementation according to docs/requirements/CODEX_ETS_PROTOCOL_REQUIREMENTS.md. Work sprint by sprint. Do not skip tests. Every protocol behavior must have a unit, integration, or conformance test. Preserve patent/IP review warnings. Do not publish secrets, private keys, personal data, or attorney-client material. Prefer deterministic behavior, explicit schemas, and independently verifiable outputs.
```
