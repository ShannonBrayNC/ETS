# IPQ-A Frozen Core / Verify / Persistence Execution

Parent: #318  
Execution sprint: #350  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Rule

The frozen SUT is immutable. The qualification harness checks out the exact SUT into `sut/`, executes only baseline-native product/tests there, and records both `sut_sha` and `harness_sha` in retained artifacts. Later protocol work cannot retroactively make a frozen row pass.

## Evidence groups

### Core / Verify

The first detached group executes baseline-native append-log, Merkle root, inclusion-proof, verifier, golden verifier/CLI, tree-head signing-envelope, and certificate claim-safety tests. These tests are candidate evidence for C01-C03 only; final row status must be mapped from the exact assertions actually reproduced.

### RFC 6962 consistency boundary

C04 is deliberately separated. A source/test search is discovery evidence only and can never produce PASS. If the frozen SUT lacks executable consistency-proof generation/verification, C04 is recorded as FAIL/EXCLUDED with #194 linked as post-baseline conformance work. If relevant frozen support is found, an executable detached test must be added before C04 can pass.

### Persistence / artifacts

The second detached group executes frozen artifact registry, artifact model, SQLite artifact registry, and SQLite event-store tests. Final P01-P05 status must distinguish restart/reopen persistence, proof-after-restart, duplicate semantics, corrupt-metadata failure and raw-byte non-retention according to assertions actually executed; implementation presence is not sufficient.

## Collector semantics

Pytest exit `0` is retained as a group PASS, exit `1` as a frozen-product group FAIL, and collection/internal/no-test errors fail the harness. A green group means only that the selected baseline-native tests passed; the result record still maps individual matrix rows conservatively.

## Nonclaims

No source truth/completeness, legal admissibility, regulatory compliance, production GA, HA, hardware attestation, or post-baseline protocol feature is established by this execution.
