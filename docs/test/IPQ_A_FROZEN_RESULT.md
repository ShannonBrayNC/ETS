# IPQ-A Frozen Core / Verify / Persistence Result

Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`  
Qualification sprint: #350  
Harness PR: #353  
Initial strengthened evidence run: `31860458736`

## Result summary

The detached IPQ-A harness executed the selected frozen Core/Verify and SQLite persistence/restart suites against the immutable SUT. No frozen product file was patched or rewritten.

| Area | Result | Reproduced evidence |
|---|---|---|
| Append / Merkle root / inclusion proof | **PASS** | Frozen append-log, Merkle and inclusion-proof suites plus API inclusion proof round-trip executed successfully. |
| Inclusion verification and tamper rejection | **PASS** | Verifier/golden/CLI suites pass; API verification accepts a valid inclusion proof and rejects a tampered root without hidden server state. |
| Offline proof bundle | **PASS** | Frozen `/api/v1/bundles/{event_id}` integration path returns the event, tree head, inclusion proof and a valid offline verification result. |
| Verification certificate | **PASS (Markdown path)** | Frozen certificate claim-safety tests pass and the certificate-report integration path renders the verification bundle in Markdown. No claim is made here for every possible export format. |
| ETS consistency proof generation / verification | **PASS — ETS v1 linear proof** | Frozen verifier/API tests exercise consistency generation and verification, including tampered-latest-root rejection. The frozen `ets.consistency_proof.v1` proof carries the full leaf-hash sequence and is not represented as compact RFC 6962 conformance. |
| Compact RFC 6962 consistency proof conformance | **EXCLUDED / POST-BASELINE** | #194 remains the dedicated compact RFC 6962 protocol-conformance sprint. This later requirement is not silently attributed to `75927c5...`. |
| Durable event persistence across reopen/restart | **PASS** | Frozen SQLite event-store and API persistence tests reopen persisted state, retain prior events/tree state and continue appending from the recovered log. |
| Artifact persistence and proof after restart | **PASS** | Frozen artifact-route SQLite restart test registers an artifact, reopens the registry, reads it after restart and verifies its proof. |
| Duplicate persistence semantics | **PASS** | Frozen artifact/event persistence tests exercise deterministic duplicate rejection / no duplicate durable row behavior. |
| Corrupt durable metadata fails closed | **PASS** | Frozen API security/persistence coverage rejects corrupt persisted hash/state instead of silently accepting it. |
| Raw artifact bytes outside durable metadata storage | **PASS (tested SQLite boundary)** | Frozen artifact restart test confirms the registered raw `artifact_bytes` sequence is not present in the SQLite database bytes. |
| Source truth / legal admissibility / compliance | **EXCLUDED** | Cryptographic and persistence behavior does not establish upstream truth, legal admissibility or regulatory compliance. |

## Initial retained evidence

### Core / Verify

- run: `31860458736`
- job: `94952827777`
- tests: `65 passed, 1 warning in 3.56s`
- artifact: `ipq-a-frozen-core`
- artifact ID: `9240401305`
- artifact ZIP SHA-256: `2a1fad7343cd1f02f5463a26c0b02c8b808c22c27f0885da330556304e4c451d`

The retained consistency-boundary artifact records:

- `status=PASS_ETS_V1_LINEAR_CONSISTENCY`
- compact RFC 6962 conformance is not claimed;
- post-baseline reference: #194.

### Persistence / artifacts

- run: `31860458736`
- job: `94952827698`
- tests: `43 passed, 1 warning in 2.35s`
- artifact: `ipq-a-frozen-persistence`
- artifact ID: `9240400741`
- artifact ZIP SHA-256: `04f49a6c8563e2fca362aa54e91d78e5c1655f67773ee48b570aa1bff6d252e4`

## Interpretation

The strongest frozen-baseline claim is that ETS Core can append canonical events, construct Merkle/inclusion evidence, verify valid and tampered inclusion/consistency material, emit an offline proof bundle and Markdown verification certificate, and recover durable event/artifact metadata across SQLite reopen/restart while failing closed on the tested corrupt state.

The consistency result is intentionally narrow: the frozen system has an executable ETS-v1 consistency mechanism, but this record does not call it compact RFC 6962 consistency proof conformance. That later conformance target remains #194.

## Final exact-head qualification

This result file moves the qualification-harness head. The preliminary repository gates and evidence run above remain useful retained frozen evidence, but final merge requires the #353 branch to be synchronized to the then-current `main`, rerun the detached IPQ-A collector and repository CI/Security/CodeQL/Formal/Benchmarks/Apalache/Lean gates on that exact head, and receive fresh independent review.

## Nonclaims

This result does not establish source truth/completeness, legal admissibility, regulatory compliance, production GA, high availability, hardware attestation or compact RFC 6962 consistency proof conformance.
