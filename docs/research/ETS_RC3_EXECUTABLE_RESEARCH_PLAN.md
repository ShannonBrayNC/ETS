# ETS RC3 Executable Research Plan
## Formal Proofs, TLA+ Specifications, Benchmarks, Experimental Results, and Multi-Node Prototype

**Status:** RC3 execution blueprint  
**Purpose:** Convert ETS from research architecture into an executable, testable, formally modeled, benchmarked protocol research platform.

---

## 1. Objective

RC2 established ETS as a generalized evidence-verification architecture. RC3 must make it executable.

RC3 deliverables:

1. Formal proof framework.
2. Executable TLA+ specification.
3. Alloy modeling path.
4. Synthetic benchmark datasets.
5. Experiment harness.
6. Baseline experimental results.
7. Live multi-node transparency prototype.
8. Independent verifier federation prototype.
9. Reproducibility package.
10. Peer-review hardening report.

---

## 2. Research Questions

### RQ1 — Integrity
Can ETS detect evidence mutation under defined cryptographic assumptions?

### RQ2 — Append-Only Correctness
Can ETS preserve historical log state across appends without permitting silent deletion or mutation?

### RQ3 — Proof Efficiency
Can ETS verify inclusion proofs with logarithmic complexity relative to log size?

### RQ4 — Federated Verification
Can independent verifiers detect log forks or root disagreement across nodes?

### RQ5 — Completeness and Omission
Can ETS detect or probabilistically flag missing expected events?

### RQ6 — Privacy-Preserving Verification
Can ETS prove integrity without exposing protected event content?

---

## 3. Formal Proof Track

### 3.1 Formal Objects

Define an ETS system:

```text
ETS = (E, C, H, L, M, P, V, W)
```

Where:

- `E` = set of evidence objects
- `C` = canonicalization function
- `H` = cryptographic hash function
- `L` = append-only log
- `M` = Merkle tree constructor
- `P` = proof generator
- `V` = verifier
- `W` = witness / federation layer

### 3.2 Assumptions

A1. `H` is collision resistant.  
A2. `C` is deterministic.  
A3. Log append operations are serialized per node.  
A4. Verifiers receive the claimed root and proof artifacts.  
A5. Honest verifiers execute protocol rules exactly.

### 3.3 Invariants

#### I1 — Hash Integrity

```text
For every evidence object e:
V_hash(e) = true iff e.hash = H(C(e_without_hash))
```

#### I2 — Append-Only Growth

```text
For every log state n:
L_n is a prefix of L_n+1
```

#### I3 — Sequence Monotonicity

```text
For every i,j where i < j:
L[i].sequence < L[j].sequence
```

#### I4 — Merkle Inclusion Soundness

```text
VerifyInclusion(e.hash, proof, root) = true implies e.hash is represented in Leaves(root)
```

#### I5 — Fork Detectability

```text
If two roots exist for the same log size and differ, federation detects disagreement when roots are gossiped.
```

#### I6 — Omission Suspicion

```text
If expected event transition T is absent within interval Δ, system emits MissingEventSuspect.
```

### 3.4 Proof Sketches

#### Theorem 1 — Evidence Tamper Detection

Given deterministic canonicalization and collision-resistant hashing, any modification to an evidence object after hash assignment is detected by hash verification except with negligible probability.

Proof sketch:

1. Let original evidence `e` produce hash `h = H(C(e))`.
2. Let modified evidence be `e_prime` where `C(e_prime) != C(e)`.
3. Verification accepts only if `H(C(e_prime)) = h`.
4. This requires finding a second preimage for `H`.
5. Under collision and second-preimage resistance, probability is negligible.

#### Theorem 2 — Append-Only Violation Detection

If log state `L_n` is committed by root `r_n`, and later state `L_m` excludes or mutates an entry from `L_n`, then consistency verification fails unless the adversary can forge a valid consistency proof.

Proof sketch:

1. `r_n` commits to all leaves in `L_n`.
2. `L_m` must contain `L_n` as prefix.
3. Removing or mutating any leaf changes the tree path and root.
4. A consistency proof must show append-only extension.
5. A non-prefix history cannot satisfy the proof relation.

#### Theorem 3 — Inclusion Proof Efficiency

For a balanced binary Merkle tree with `n` leaves, inclusion proof length is `O(log n)`.

Proof sketch:

1. Inclusion path contains one sibling hash per tree level.
2. Balanced binary tree height is `ceil(log2 n)`.
3. Proof length grows with height.

#### Theorem 4 — Federation Fork Detection

If two honest verifiers observe different roots for identical `(logId, treeSize, epoch)`, then a fork is detectable by root gossip.

Proof sketch:

1. Honest verifiers publish observed root tuples.
2. Equality condition requires identical root for same log state tuple.
3. Conflicting roots violate uniqueness.
4. Detection requires only comparison, not full log reconstruction.

---

## 4. Executable TLA+ Track

### 4.1 Model Targets

The TLA+ model must verify:

- append-only log behavior
- monotonic sequence numbers
- hash-link continuity abstraction
- no mutation of committed entries
- verifier root agreement
- fork detection through gossip

### 4.2 Files to Create

```text
formal/tla/ETSLog.tla
formal/tla/ETSLog.cfg
formal/tla/README.md
```

### 4.3 TLC Properties

Properties:

- TypeOK
- AppendOnly
- SequenceMonotonic
- NoMutation
- RootAgreementOrForkDetected

---

## 5. Alloy Track

### 5.1 Model Targets

Alloy should model:

- evidence object relationships
- causal sequence graphs
- invalid state transitions
- omission patterns
- verifier federation disagreement

### 5.2 Files to Create

```text
formal/alloy/ETSEvidence.als
formal/alloy/README.md
```

---

## 6. Benchmark Dataset Track

### 6.1 Synthetic Dataset Families

Create deterministic synthetic datasets under:

```text
benchmarks/datasets/
```

Required datasets:

1. `ticketing_small.jsonl` — 1,000 events
2. `ticketing_medium.jsonl` — 100,000 events
3. `ai_decisions_small.jsonl` — 1,000 events
4. `transactions_small.jsonl` — 1,000 events
5. `governance_small.jsonl` — 1,000 events
6. `tampered_events.jsonl` — mutation injection dataset
7. `missing_events.jsonl` — omission injection dataset
8. `forked_roots.jsonl` — federation conflict dataset

### 6.2 Dataset Requirements

Each event must include:

- schemaVersion
- eventId
- correlationId
- sequence
- timestamp
- actor
- action
- eventType
- inputs
- outputs
- context

No real PII may be used.

### 6.3 Reproducibility

Dataset generator must accept:

```text
--seed
--count
--domain
--out
--tamper-rate
--missing-rate
```

---

## 7. Experiment Harness Track

### 7.1 Required Benchmarks

Benchmark suites:

1. Canonicalization throughput.
2. Hash throughput.
3. Append latency.
4. Merkle tree construction time.
5. Inclusion proof generation latency.
6. Inclusion proof verification latency.
7. Multi-node root propagation latency.
8. Fork detection time.
9. Missing-event suspicion accuracy.

### 7.2 Output Format

Results must be emitted as:

```text
benchmarks/results/*.json
benchmarks/results/*.md
```

### 7.3 Baseline Metrics

Minimum baseline metrics:

- events/sec canonicalized
- events/sec hashed
- append p50/p95/p99 latency
- proof generation p50/p95/p99
- proof verification p50/p95/p99
- memory usage estimate
- proof size distribution

---

## 8. Multi-Node Prototype Track

### 8.1 Prototype Goal

Implement a local multi-node ETS transparency cluster.

Minimum cluster:

- 3 log nodes
- 2 verifier nodes
- 1 witness/gossip node

### 8.2 Node Types

#### Log Node

Responsibilities:

- accept evidence
- append to local log
- compute roots
- expose proof endpoints

#### Verifier Node

Responsibilities:

- retrieve evidence
- verify hashes
- verify proofs
- compare roots

#### Witness Node

Responsibilities:

- collect signed or unsigned roots
- detect root disagreement
- publish federation status

### 8.3 Local Deployment

Required local orchestration:

```text
docker-compose.yml
```

or equivalent script:

```text
scripts/run-local-federation.ps1
scripts/run-local-federation.sh
```

### 8.4 Required Endpoints

```text
POST /evidence
GET /evidence/{eventId}
GET /log/root
GET /proof/inclusion/{eventId}
POST /verify/evidence
POST /verify/inclusion
POST /witness/root
GET /witness/status
```

---

## 9. Experimental Results Track

### 9.1 Required Reports

Create:

```text
benchmarks/results/BASELINE_RESULTS.md
benchmarks/results/BASELINE_RESULTS.json
```

### 9.2 Baseline Experiments

Run and record:

1. 1,000-event append test.
2. 10,000-event append test.
3. Inclusion proof verification test.
4. Tamper detection test.
5. Missing-event injection test.
6. Forked-root detection test.

### 9.3 Report Requirements

Each result must include:

- machine
- OS
- runtime
- date
- git commit
- dataset
- command
- metrics
- interpretation
- limitations

---

## 10. Independent Verifier Federation

### 10.1 Federation Model

Federation tuple:

```text
(logId, epoch, treeSize, rootHash, verifierId, observedAt)
```

### 10.2 Conflict Rule

If two tuples share:

```text
(logId, epoch, treeSize)
```

but differ by:

```text
rootHash
```

then emit:

```text
ForkDetected
```

### 10.3 Quorum Research

Future versions must explore:

- m-of-n verifier agreement
- verifier reputation
- regulator witness nodes
- public observer nodes

---

## 11. Peer-Review Simulation Critique

### 11.1 Expected Reviewer Objection: Novelty

Concern:

ETS combines known primitives.

Response:

The research novelty is not individual cryptographic primitives, but the generalized protocol integration of evidence semantics, operational verifiability, AI decision evidence, omission research, and federated transparency validation.

### 11.2 Expected Reviewer Objection: Completeness

Concern:

ETS cannot prove uncaptured events.

Response:

Correct. RC3 explicitly treats completeness as an open research problem and introduces omission suspicion rather than overstated guarantees.

### 11.3 Expected Reviewer Objection: Performance

Concern:

Cryptographic verification adds overhead.

Response:

RC3 requires benchmark data to quantify overhead, identify selective capture strategies, and distinguish critical-event evidence from ordinary telemetry.

### 11.4 Expected Reviewer Objection: Blockchain Similarity

Concern:

ETS is rebranded blockchain.

Response:

ETS does not require economic consensus, tokenization, or global decentralized ledgers. Blockchain may be used only as optional anchoring.

---

## 12. RC3 Definition of Done

RC3 is complete when:

- Formal proof document exists.
- TLA+ model runs under TLC.
- Alloy model exists or is explicitly deferred.
- Synthetic dataset generator exists.
- Benchmark harness runs locally.
- Baseline results are committed.
- Multi-node local prototype runs.
- Verifier federation detects root disagreement.
- Peer-review critique document exists.
- README links all RC3 materials.

---

## 13. Codex Execution Prompt

```text
You are working in ShannonBrayNC/ETS.

Implement ETS RC3 according to docs/research/ETS_RC3_EXECUTABLE_RESEARCH_PLAN.md.

Work in this order:

1. Add formal proof docs.
2. Add executable TLA+ model.
3. Add benchmark dataset generator.
4. Add benchmark harness.
5. Add minimal ETS core implementation if missing.
6. Add append-only log and Merkle proof implementation.
7. Add multi-node local prototype.
8. Add verifier federation root gossip.
9. Add baseline benchmark results.
10. Add peer-review critique report.

Rules:

- Every function must have tests.
- Every benchmark must be reproducible.
- Do not use real PII.
- Preserve patent-review warnings.
- Do not overclaim completeness.
- Treat omission detection as probabilistic/suspicion-based unless formally proven.
- Favor deterministic outputs.
- Add README links.
```
