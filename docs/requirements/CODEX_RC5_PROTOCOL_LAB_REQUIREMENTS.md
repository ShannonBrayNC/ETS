# Codex Requirements — ETS RC5 Protocol Lab

## Purpose

This file defines the RC5 implementation plan for moving ETS from RC4 executable scaffolding into a runnable protocol research laboratory.

RC5 must add:

1. FastAPI verification service
2. Inclusion proof generation APIs
3. Consistency proofs
4. Ed25519 signing
5. Docker federation cluster
6. GitHub Actions benchmark automation
7. TLC execution validation in CI
8. Real benchmark result publication
9. Fork simulation harness
10. Omission-detection experiments
11. zk-proof branch scaffold
12. IEEE paper formatting
13. Full theorem formalization
14. Protocol RFC structure
15. Independent verifier quorum algorithms

---

## Non-Negotiable Engineering Rules

- Every protocol function must have unit tests.
- Every API endpoint must have integration tests.
- Every benchmark must be reproducible.
- Every experiment must write machine-readable and human-readable results.
- No real PII may be used in datasets or fixtures.
- Do not claim completeness where only omission suspicion exists.
- Preserve patent-review warnings in public-facing docs.
- Prefer deterministic output over cleverness.
- Keep implementation minimal, auditable, and well tested.

---

# Sprint 1 — FastAPI Verification Service

## Required Files

```text
src/ets/api/main.py
src/ets/api/models.py
src/ets/api/dependencies.py
tests/integration/test_api.py
```

## Required Endpoints

```text
GET  /health
POST /evidence
GET  /evidence/{event_id}
GET  /log/root
GET  /log/size
GET  /proof/inclusion/{event_id}
POST /verify/evidence
POST /verify/inclusion
```

## Behavior

- `/evidence` appends a valid evidence object to an append-only transparency node.
- `/evidence/{event_id}` returns stored evidence.
- `/log/root` returns current Merkle root.
- `/log/size` returns number of evidence records.
- `/proof/inclusion/{event_id}` returns inclusion proof.
- `/verify/evidence` verifies canonical hash integrity.
- `/verify/inclusion` verifies inclusion proof against root.

## Acceptance Criteria

- API starts locally with `uvicorn ets.api.main:app`.
- OpenAPI is available at `/docs`.
- Integration tests pass.
- Tampered evidence verification fails.
- Unknown event IDs return deterministic 404 errors.

---

# Sprint 2 — Inclusion Proof Generation APIs

## Required Files

```text
src/ets/merkle/proofs.py
tests/unit/test_inclusion_proofs.py
```

## Required Functions

```python
create_inclusion_proof(leaf_hash: str, leaves: list[str]) -> dict
verify_inclusion_proof(leaf_hash: str, proof: dict, root: str) -> bool
```

## Proof Format

```json
{
  "leafHash": "string",
  "leafIndex": 0,
  "treeSize": 1,
  "path": [
    {
      "position": "left|right",
      "hash": "string"
    }
  ]
}
```

## Tests

- Single leaf proof succeeds.
- Even leaf count proof succeeds.
- Odd leaf count proof succeeds.
- Modified leaf fails.
- Modified path hash fails.
- Wrong root fails.
- 1,000-leaf proof succeeds.

---

# Sprint 3 — Consistency Proofs

## Required Files

```text
src/ets/merkle/consistency.py
tests/unit/test_consistency_proofs.py
docs/spec/CONSISTENCY_PROOFS.md
```

## Required Functions

```python
create_consistency_proof(old_size: int, new_size: int, leaves: list[str]) -> dict
verify_consistency_proof(old_root: str, new_root: str, proof: dict) -> bool
```

## Scope

RC5 may implement a simplified consistency proof first, but it must document limitations and must not falsely claim RFC 6962 equivalence unless implemented faithfully.

## Acceptance Criteria

- Valid append-only growth verifies.
- Reordered history fails.
- Removed historical leaf fails.
- Mutated historical leaf fails.
- Limitations are documented.

---

# Sprint 4 — Ed25519 Signing

## Required Files

```text
src/ets/crypto/signing.py
tests/unit/test_signing.py
docs/security/KEY_MANAGEMENT.md
```

## Required Functions

```python
generate_keypair() -> tuple[str, str]
sign_evidence(evidence: dict, private_key: str, key_id: str) -> dict
verify_signature(evidence: dict, public_key: str) -> bool
```

## Dependency

Use a well-maintained Python cryptography library.

## Tests

- Valid signature passes.
- Modified evidence fails.
- Wrong public key fails.
- Missing signature fails clearly.
- Signature excludes `signature.value` from signed payload.

## Security Requirements

- Never commit real private keys.
- Test keys must be clearly marked as fixtures.
- Key rotation model must be documented.

---

# Sprint 5 — Docker Federation Cluster

## Required Files

```text
docker-compose.yml
Dockerfile
scripts/run-local-federation.sh
scripts/run-local-federation.ps1
```

## Cluster Layout

- `ets-log-node-a`
- `ets-log-node-b`
- `ets-log-node-c`
- `ets-verifier-a`
- `ets-verifier-b`
- `ets-witness`

## Acceptance Criteria

- `docker compose up` starts local cluster.
- Each log node exposes API.
- Witness receives root observations.
- Fork simulation can trigger `ForkDetected`.

---

# Sprint 6 — GitHub Actions Benchmark Automation

## Required Files

```text
.github/workflows/ci.yml
.github/workflows/benchmarks.yml
benchmarks/results/README.md
```

## CI Jobs

- Install dependencies.
- Run unit tests.
- Run integration tests.
- Run benchmark smoke test.
- Validate docs formatting where practical.

## Benchmark Workflow

- Run deterministic benchmark with small dataset.
- Save JSON result artifact.
- Save Markdown summary artifact.

## Acceptance Criteria

- CI passes on pull request.
- Benchmark artifact is produced.
- Benchmark command is documented.

---

# Sprint 7 — TLC Execution Validation in CI

## Required Files

```text
.github/workflows/tla.yml
formal/tla/README.md
```

## Behavior

- Download or install TLA+ tools.
- Run TLC against `formal/tla/ETSLog.tla` and `ETSLog.cfg`.
- Fail CI on invariant violations.

## Acceptance Criteria

- TLC workflow exists.
- TLC command is documented.
- CI failure semantics are clear.

---

# Sprint 8 — Real Benchmark Result Publication

## Required Files

```text
benchmarks/results/BASELINE_RESULTS.json
benchmarks/results/BASELINE_RESULTS.md
benchmarks/results/RESULT_SCHEMA.json
```

## Required Metrics

- canonicalization events/sec
- hash events/sec
- append events/sec
- Merkle build time
- inclusion proof generation p50/p95/p99
- inclusion proof verification p50/p95/p99
- memory approximation
- machine/runtime metadata
- git commit hash

## Acceptance Criteria

- Results are reproducible.
- Hardware/runtime metadata is included.
- Limitations are clearly stated.

---

# Sprint 9 — Fork Simulation Harness

## Required Files

```text
src/ets/experiments/fork_simulation.py
tests/integration/test_fork_simulation.py
docs/experiments/FORK_SIMULATION.md
```

## Behavior

- Create two log histories for same `(logId, treeSize)`.
- Submit conflicting roots to witness.
- Witness emits `ForkDetected`.

## Acceptance Criteria

- Simulation runs locally.
- Test asserts fork detection.
- Report explains expected behavior.

---

# Sprint 10 — Omission-Detection Experiments

## Required Files

```text
src/ets/experiments/omission_detection.py
tests/unit/test_omission_detection.py
docs/experiments/OMISSION_DETECTION.md
```

## Required Concepts

- expected event transition
- allowed time interval
- missing-event suspicion
- false-positive discussion
- false-negative discussion

## Required Function

```python
detect_missing_transitions(events: list[dict], expected_model: dict) -> list[dict]
```

## Acceptance Criteria

- Known missing transition is detected.
- Complete sequence produces no findings.
- Out-of-order events are handled deterministically.
- Documentation explicitly states this is suspicion, not proof of completeness.

---

# Sprint 11 — zk-Proof Branch Scaffold

## Required Files

```text
docs/research/ZK_ETS_EXTENSION.md
src/ets/zk/README.md
```

## Scope

RC5 does not require production zk-SNARK implementation.

It must define:

- privacy-preserving verification goals
- candidate proof systems
- example statements
- threat model
- future implementation plan

## Example Statement

```text
Prove that an evidence object exists in a committed log and satisfies policy P without revealing protected fields.
```

## Acceptance Criteria

- Research scaffold exists.
- No unsupported claims of zk production readiness.

---

# Sprint 12 — IEEE Paper Formatting

## Required Files

```text
docs/research/ieee/ETS_IEEE_DRAFT.md
docs/research/ieee/README.md
```

## Required Sections

- Abstract
- Introduction
- Background
- Problem Statement
- System Model
- Threat Model
- Protocol Design
- Formal Properties
- Implementation
- Evaluation
- Related Work
- Limitations
- Future Work
- Conclusion
- References

## Acceptance Criteria

- Paper reads like an academic systems paper.
- Claims are bounded and testable.
- Experimental sections reference benchmark artifacts.

---

# Sprint 13 — Full Theorem Formalization

## Required Files

```text
docs/research/FORMAL_THEOREMS.md
```

## Required Theorems

1. Evidence Tamper Detection
2. Append-Only Violation Detection
3. Inclusion Proof Soundness
4. Fork Detection by Federation
5. Deterministic Canonicalization Stability
6. Omission Suspicion Soundness Boundaries

## Required Format

Each theorem must include:

- Statement
- Assumptions
- Definitions
- Proof sketch
- Limitations
- Test/experiment mapping

---

# Sprint 14 — Protocol RFC Structure

## Required Files

```text
docs/spec/rfc/ETS-RFC-0001.md
docs/spec/rfc/ETS-RFC-0002-EVIDENCE.md
docs/spec/rfc/ETS-RFC-0003-PROOFS.md
docs/spec/rfc/ETS-RFC-0004-FEDERATION.md
```

## Requirements

Use RFC-style structure:

- Status
- Abstract
- Terminology
- Protocol Requirements
- Wire Formats
- Security Considerations
- Privacy Considerations
- IANA Considerations if applicable
- References

## Acceptance Criteria

- Protocol is implementable from RFC docs.
- Normative language is used consistently.

---

# Sprint 15 — Independent Verifier Quorum Algorithms

## Required Files

```text
src/ets/federation/quorum.py
tests/unit/test_quorum.py
docs/spec/VERIFIER_QUORUM.md
```

## Required Functions

```python
has_quorum(observations: list[dict], threshold: int) -> bool
detect_conflicts(observations: list[dict]) -> list[dict]
select_consensus_root(observations: list[dict], threshold: int) -> dict | None
```

## Required Behavior

- m-of-n verifier agreement.
- conflicting root detection.
- abstention / missing verifier handling.
- deterministic consensus root selection.

## Acceptance Criteria

- Quorum success test.
- Quorum failure test.
- Conflict detection test.
- Deterministic tie handling test.

---

# Definition of Done for RC5

RC5 is complete when:

- FastAPI service runs locally.
- Inclusion proofs are generated and verified.
- Consistency proofs exist with documented limitations.
- Ed25519 signing works.
- Docker federation cluster starts.
- GitHub Actions test workflow exists.
- Benchmark workflow exists.
- TLC validation workflow exists.
- Baseline benchmark results are published.
- Fork simulation harness works.
- Omission-detection experiment works.
- zk extension scaffold exists.
- IEEE draft exists.
- Formal theorem document exists.
- RFC-style protocol docs exist.
- Quorum algorithms are implemented and tested.

---

# Codex Bootstrap Prompt

```text
You are working in ShannonBrayNC/ETS.

Implement RC5 according to docs/requirements/CODEX_RC5_PROTOCOL_LAB_REQUIREMENTS.md.

Proceed sprint by sprint. Do not skip tests. Do not overclaim completeness. Keep the protocol patent-aware and research-grade. Every new function must have tests. Every API endpoint must have integration coverage. Every experiment must produce reproducible output. Use deterministic fixtures and no real PII.
```
