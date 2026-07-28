# ETS Protocol Adoption Roadmap

## Purpose

This roadmap defines the step-by-step path for making ETS known, testable, and reviewable as a protocol rather than only as a product implementation.

ETS is the Evidence Transparency System. The public protocol scope is submitted-event metadata, content hashes, canonicalization, append-only transparency logging, Merkle inclusion proofs, tree-head comparison, verification certificates, policy-gated routing, and audit replay.

This document is public-safe. It must not include USPTO receipts, application numbers, confirmation numbers, filing drafts, claim charts, prior-art matrices, attorney-review notes, assignment strategy, customer evidence, secrets, or private Lantern-IP materials.

## Protocol Boundary

ETS should be implementable without Lantern, EchoMedia, Christina, SignalForge, OpsHelm, or any private repository. Those systems may be adopters, reference integrations, or demonstration environments, but the protocol must stand on its own.

ETS verifies submitted-event metadata, content hashes, proof material, tree-head progression, verification certificate outputs, policy decisions, and replayable audit records within defined protocol boundaries.

ETS does not prove real-world truth, legal sufficiency, official chain of custody, election correctness, vote totals, ballot validity, or completeness without an external expected-event policy and observation process.

For civic and election-adjacent evidence, ETS must remain framed as an evidence/audit layer. ETS is not voting software, tabulation software, voter-registration software, ballot software, election-correctness software, or the vote of record unless separately certified and legally designated.

## Adoption Definition

ETS is known when:

- A public protocol specification exists.
- A public repository is safe, readable, and free of private IP artifacts.
- A clear technical problem statement exists.
- ETS is compared honestly to related transparency, provenance, signing, policy, and audit systems.
- Technical communities have been asked to review it.
- Prime partners and public-sector evaluators can understand where it fits.

ETS is tested when:

- Public test vectors exist.
- A reference implementation passes the vectors.
- An independent verifier passes the vectors.
- A conformance runner exists.
- An interoperability report exists.
- A threat model exists.
- A pilot report exists.

ETS is functioning as a protocol when:

- Someone else can implement it without using private ETS code.
- Someone else can independently verify ETS outputs.
- At least two implementations produce the same hashes, proofs, certificates, and routing states for the same test vectors.
- The specification explains what is required, optional, and forbidden.

## Phase 1: Public Protocol Framing

Goal: make the public boundary clear before inviting review.

Tasks:

- Create `/spec/ets-core-protocol.md`.
- Create `/spec/ets-evidenceevent-schema.md`.
- Create `/spec/ets-proof-format.md`.
- Create `/spec/ets-certificate-format.md`.
- Create `/spec/ets-policy-routing.md`.
- Ensure `PATENT_NOTICE.md` says ETS is patent pending without exposing private filing information.
- Ensure README boundaries are public-safe.
- Ensure private IP materials remain outside the public repo.

Public positioning:

> ETS is an Evidence Transparency System protocol for submitted-event metadata, content hashes, canonicalization, append-only transparency logs, Merkle proofs, verification certificates, policy-gated routing, and audit replay.

## Phase 2: ETS Protocol v0.1

Goal: publish a protocol document that another engineer can implement.

`/spec/ets-core-protocol.md` should include:

1. Abstract
2. Terminology
3. Roles
4. EvidenceEvent object
5. Canonicalization rules
6. Hashing rules
7. Append-only log behavior
8. Merkle inclusion proof format
9. Tree-head format
10. Verification certificate format
11. Policy-gated routing behavior
12. Audit replay behavior
13. Security considerations
14. Privacy considerations
15. Non-claims and civic/election boundary
16. Media type and registry considerations, future
17. Conformance requirements

Requirement language should use:

- MUST
- MUST NOT
- SHOULD
- SHOULD NOT
- MAY

The protocol document should be precise enough for tests to enforce behavior and plain enough for external review.

## Phase 3: Standards Alignment

Goal: show that ETS understands the surrounding ecosystem and is designed to interoperate rather than pretend existing work does not exist.

Alignment anchors:

- JSON canonicalization: RFC 8785 / JSON Canonicalization Scheme.
- Transparency logs and Merkle proofs: Certificate Transparency / RFC 9162 patterns.
- Supply-chain signed statement transparency: SCITT / RFC 9943 patterns.
- Software artifact and provenance ecosystems: Sigstore, Rekor, SLSA, OpenSSF.
- Content provenance ecosystems: C2PA / Content Credentials.
- Policy-as-code ecosystems: Open Policy Agent and related policy engines.

Compatibility language:

> ETS may use RFC 8785-compatible canonical JSON for hashable EvidenceEvent payloads.

> ETS may use Merkle inclusion and tree-head verification patterns compatible with established transparency-log architectures.

> ETS may interoperate with SCITT-style signed statement and receipt systems while adding EvidenceEvent classification, verification certificates, claim boundaries, policy-gated routing, and audit replay.

## Phase 4: Minimum Reference Implementation

Goal: prove the protocol is executable.

The first reference implementation should do only this:

1. Accept an EvidenceEvent JSON object.
2. Validate the schema.
3. Canonicalize the event.
4. Compute `event_hash`.
5. Append to a local log.
6. Update the Merkle root.
7. Generate an inclusion proof.
8. Verify the inclusion proof.
9. Generate a verification certificate.
10. Apply a simple policy route.
11. Replay verification by `event_id`.

Minimum API:

```http
POST /v1/events
GET  /v1/events/{event_id}
GET  /v1/events/{event_id}/proof
GET  /v1/tree/head
POST /v1/verify
GET  /v1/certificates/{certificate_id}
POST /v1/replay/{event_id}
```

Minimum CLI:

```bash
ets event validate event.json
ets event hash event.json
ets log append event.json
ets proof get <event_id>
ets proof verify proof.json
ets cert generate <event_id>
ets replay <event_id>
```

## Phase 5: Test Vectors

Goal: make ETS testable by people who do not trust the reference implementation.

Create:

```text
/test-vectors/valid/event-basic.json
/test-vectors/valid/event-with-external-ref.json
/test-vectors/valid/event-policy-review.json
/test-vectors/invalid/missing-schema-version.json
/test-vectors/invalid/bad-content-hash.json
/test-vectors/invalid/noncanonical-key-order.json
/test-vectors/invalid/proof-root-mismatch.json
/test-vectors/edge-cases/unicode.json
/test-vectors/edge-cases/large-metadata.json
/test-vectors/edge-cases/redacted-evidence.json
```

Each vector should include or reference:

- Input event.
- Canonical text or canonical bytes.
- Expected `event_hash`.
- Expected `leaf_hash`.
- Expected proof result.
- Expected certificate result.
- Expected policy route.

Example manifest:

```json
{
  "vector_id": "ets-v0.1-valid-basic-001",
  "input": "event-basic.json",
  "expected": {
    "canonicalization_profile": "ets-jcs-v0.1",
    "event_hash": "sha256:...",
    "leaf_hash": "sha256:...",
    "proof_verified": true,
    "certificate_status": "verified",
    "policy_route": "human_review"
  }
}
```

## Phase 6: Conformance Suite

Goal: let anyone test whether an implementation is ETS-compatible.

Create:

```text
/conformance/ets-conformance-runner.py
/conformance/ets-conformance-profile-v0.1.md
```

Conformance profiles:

### ETS-Core

- EvidenceEvent schema validation.
- Canonicalization.
- Event hash.
- Content hash reference.
- Append log.
- Inclusion proof.
- Verification certificate.

### ETS-Transparency

- Merkle tree root.
- Inclusion proof verification.
- Tree-head comparison.
- Rollback detection.
- Fork detection.
- Stale-state detection.

### ETS-Policy

- Evidence states.
- Routing outcomes.
- Human review.
- Quarantine.
- Reject.
- Archive.
- Restrict release.

### ETS-Replay

- Event lookup.
- Proof reconstruction.
- Certificate regeneration.
- Replay report.

Target command:

```bash
ets-conformance run \
  --implementation-url http://localhost:8080 \
  --profile ets-core-v0.1 \
  --vectors ./test-vectors
```

Expected output:

```text
ETS Conformance Report
Profile: ets-core-v0.1
Implementation: example-python
Passed: 42
Failed: 0
Warnings: 2
Result: CONFORMANT
```

## Phase 7: Public Interoperability Demo

Goal: show ETS works across implementations.

Build two implementations:

- Implementation A: Python reference server.
- Implementation B: TypeScript verifier/client.

Interop flow:

1. Python server appends an EvidenceEvent.
2. Python server generates proof.
3. TypeScript verifier independently verifies proof.
4. TypeScript verifier generates or validates the certificate.
5. Python replay reproduces the same result.
6. Both implementations produce the same hashes and verification state.

Create:

```text
docs/interop/ETS_INTEROP_DEMO_001.md
docs/interop/ETS_INTEROP_RESULTS_001.md
```

## Phase 8: Public Release Package

Goal: make ETS discoverable and reviewable.

Public release package:

```text
README.md
PATENT_NOTICE.md
/spec/ets-core-protocol.md
/spec/ets-evidenceevent-schema.md
/spec/ets-proof-format.md
/spec/ets-certificate-format.md
/test-vectors
/conformance
/examples
/docs/security/THREAT_MODEL.md
/docs/protocol/ETS_PROTOCOL_ADOPTION_ROADMAP.md
```

README language:

> ETS is patent pending and open for protocol review.
>
> This repository contains public protocol, implementation, conformance, and test-vector materials. Private patent filings, claim charts, USPTO receipts, attorney notes, and assignment records are maintained separately.

Do not publish:

- USPTO application number.
- USPTO receipts.
- Claim charts.
- Prior-art matrix.
- Private drafts.
- Attorney notes.
- Lantern-IP contents.

## Phase 9: Protocol Communities

Goal: get technical review from communities that understand protocols, transparency logs, provenance, supply-chain evidence, and governance.

Suggested sequence:

1. OpenSSF supply-chain and provenance communities.
2. Sigstore / Rekor adjacent discussions.
3. SCITT / IETF-adjacent review, after test vectors and implementation experience exist.
4. W3C Community Group path, if ETS becomes useful for web-verifiable certificates or content provenance contexts.
5. CNCF Sandbox, later, only after public repo maturity, contributors, containerized deployment, and adopters exist.

Initial review request:

> I am developing ETS, an Evidence Transparency System protocol for evidence-event hashes, inclusion proofs, verification certificates, and policy-gated routing. I am looking for feedback on the protocol boundary and test-vector strategy, especially where it overlaps or should interoperate with SCITT, Sigstore, provenance, and transparency-log work.

## Phase 10: External Pilot Tracks

Goal: test ETS with outsiders and publish public-safe case studies.

### Track A: DevSecOps Evidence

Use ETS to verify CI/CD artifacts, pull request reviews, deployment approvals, release-gate evidence, and build/deployment audit records.

### Track B: AI Workflow Governance

Use ETS to record AI-agent recommendations, human approvals, tool calls, policy-gated actions, and audit replay of AI-assisted workflow decisions.

### Track C: Emergency and Sensor Evidence

Use ETS to hash, append, verify, and replay emergency reports, outage records, RF anomalies, sensor telemetry, and weather-impact packets.

Each pilot should produce:

1. Pilot problem statement.
2. Sanitized sample evidence data.
3. ETS integration guide.
4. Test-vector bundle.
5. Verification report.
6. Lessons learned.
7. Public-safe case study.

## Ninety-Day Plan

### Days 1-7: Protocol Framing

- Create branch `protocol/ets-protocol-adoption-readiness`.
- Add `/spec/ets-core-protocol.md`.
- Add `/spec/ets-evidenceevent-schema.md`.
- Add this roadmap.
- Add public patent notice.
- Add civic/election boundary language.
- Remove private IP material from public release branches.

### Days 8-21: Testable Core

- Freeze EvidenceEvent v0.1.
- Choose canonicalization profile.
- Define hashable payload rules.
- Define `content_hash` and `event_hash` rules.
- Define Merkle proof shape.
- Define verification certificate shape.
- Define policy route outputs.
- Create 10 valid test vectors.
- Create 10 invalid test vectors.

### Days 22-35: Reference Implementation

- Build Python ETS reference server.
- Build CLI commands.
- Build TypeScript verifier.
- Add Docker Compose demo.
- Add GitHub Actions conformance test.
- Add JSON Schema validation.
- Add replay report generation.

### Days 36-50: Conformance

- Build conformance runner.
- Define ETS-Core profile.
- Define ETS-Transparency profile.
- Define ETS-Policy profile.
- Define ETS-Replay profile.
- Publish conformance report format.
- Make CI fail if reference implementation breaks vectors.

### Days 51-65: Interoperability

- Run Python-to-TypeScript verification demo.
- Add one external or minimal independent implementation.
- Publish interop report.
- Invite three technical reviewers.
- Open GitHub Discussions.
- Create protocol issues labeled `spec`, `conformance`, `interop`, and `security`.

### Days 66-80: Community Review

- Post ETS protocol introduction.
- Share OpenSSF review question.
- Compare ETS to SCITT, Sigstore, C2PA, Certificate Transparency, and OPA.
- Publish threat model.
- Publish privacy model.
- Publish non-claims page.
- Collect review notes.

### Days 81-90: Pilot Readiness

- Package DevSecOps pilot.
- Package AI-governance pilot.
- Package emergency/sensor pilot.
- Build one-page protocol brief.
- Build five-slide technical explainer.
- Identify 10 prime, agency, lab, or civic-tech contacts.
- Schedule technical review calls.

## Next Repository Steps

1. Keep this roadmap separate from private IP files.
2. Link this roadmap from the government-opportunity readiness PR.
3. Build the protocol spec skeleton.
4. Build EvidenceEvent v0.1 schema and first test vectors.
5. Run the first reference implementation against those vectors.
