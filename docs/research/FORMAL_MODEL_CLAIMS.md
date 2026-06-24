# Formal Model Claims

This document maps ETS formal artifacts to protocol claims, implementation evidence, tests, and explicit non-claims.

ETS is the **Evidence Transparency System**. These formal artifacts support restrained engineering claims about submitted evidence material. They are not a blanket proof of real-world truth, legal sufficiency, election correctness, or production trust.

## Formal Artifact Inventory

| Artifact | Purpose | Claim Level |
|---|---|---|
| `formal/tla/ETSLog.tla` | Models append-only state, bounded root observations, fork suspicion, and omission suspicion relative to an expected-event set. | Safety model |
| `formal/tla/ETSAsyncNetwork.tla` | Models bounded asynchronous queues, delivery, packet loss, and reordering as nondeterministic transitions. | Bounded network model |
| `formal/tla/ETSLiveness.tla` | Models replay eventuality, partition healing, witness propagation completion, stale-state recovery, and convergence under weak fairness assumptions. | Fairness-scoped liveness model |
| `formal/alloy/ETSCausalModel.als` | Models causal evidence relationships, tenant/workspace association, append-only uniqueness, and omission relative to an expected set. | Structural/causal model |
| `docs/research/FORMAL_THEOREMS.md` | States implementation-facing theorem obligations, assumptions, and non-theorems. | Theorem appendix |
| `docs/research/FORMAL_TRACEABILITY_MATRIX.md` | Maps formal claims to code and tests. | Traceability control |
| `docs/research/claim-traceability-manifest.json` | Machine-readable claim map for dissertation and publication gates, including models, tests, workflows, release notes, risk labels, and issue references. | Traceability control |

## TLA+ Claim Map

| TLA+ Predicate / Model Property | ETS Protocol Claim | Implementation / Test Evidence | Non-Claim |
|---|---|---|---|
| `TypeOK` | Log, observation, fork, and omission state remain within modeled bounds. | TLA+ model; implementation type checks; unit tests where applicable. | Does not prove Python runtime cannot have unrelated bugs. |
| `NoDuplicateLogEntries` | The modeled append-only log does not contain duplicate event identifiers. | `ets.core.log`; append-log tests. | Does not prove raw evidence bytes are unique. |
| `LogIndexDomainContiguous` | Log indexes are contiguous in the modeled state. | `ets.core.log`; append/retrieval tests. | Does not prove external storage cannot fail. |
| `ExpectedEventsWellFormed` | Omission detection requires a bounded external expected-event set. | `ets.experiments.omission_detection`; omission tests. | Does not prove the expected-event set is complete or authoritative. |
| `ObservedTreeSizesBounded` | Observed tree sizes must be consistent with the modeled log unless fork suspicion is active. | federation/root observation logic; federation tests. | Does not prove a remote verifier is honest. |
| `MissingSuspicionsRequireExpectation` | Missing-event findings are valid only relative to an external expectation. | omission detection logic; Alloy omission assertion; experiment tests. | Does not prove real-world completeness. |
| `MissingSuspicionsAreAbsentAtDetectionBoundary` | Missing-event suspicion only applies to expected IDs absent from the observed log at detection time. | omission detection logic; experiment tests. | Does not prove the event will remain absent forever. |
| `ForkFlagRequiresConflict` | Fork suspicion requires conflicting observed roots for the same modeled view. | federation/fork simulation; experiment tests. | Does not identify which node is honest. |

## Alloy Claim Map

| Alloy Predicate / Assertion | ETS Protocol Claim | Implementation / Test Evidence | Non-Claim |
|---|---|---|---|
| `appendOnly[l]` | A modeled log should not repeat the same event in distinct positions. | `ets.core.log`; append-log tests. | Does not prove cryptographic hash collision resistance. |
| `tenantScoped[l]` | Events carry tenant/workspace relationships that can be reasoned about structurally. | API tenant/workspace scoping; integration tests. | Does not prove hosted identity configuration is correct. |
| `observedIds[l]` | Observed event IDs are derived from log entries. | event-listing/proof lookup behavior; API tests. | Does not prove all external systems submitted events. |
| `omitted[e,l,missing]` | Omission suspicion requires an expected ID absent from observed IDs. | omission detection; experiment tests. | Does not prove the expected manifest is correct. |
| `NoDuplicateEventsInAppendOnlyLog` | Append-only modeled logs prevent duplicate event object entries. | append-log tests. | Does not prove all real-world evidence is unique. |
| `OmissionRequiresExternalExpectation` | Omission claims are scoped to an external expectation set. | omission tests; research non-claims docs. | Does not prove real-world completeness. |

## Required Non-Goals

The formal model set does not prove:

- real-world truth of submitted events;
- legal sufficiency or chain-of-custody adequacy;
- election correctness, vote totals, ballot validity, or official status;
- SHA-256 collision resistance;
- Ed25519 key custody or private-key non-compromise;
- hosted identity correctness;
- production key rotation safety;
- cloud durability;
- Byzantine consensus;
- Internet-scale adversarial liveness;
- correctness of external anchor publication media;
- completeness without an external expected-event policy and observation process.

## Test Mapping Rule

Every formal claim in public-facing research documentation must map to at least one of:

1. a TLA+ predicate, invariant, theorem, or model file;
2. an Alloy predicate/assertion/check;
3. implementation code;
4. unit/integration tests;
5. a clearly marked `pending`, `bounded model`, `fairness-scoped`, `statistical only`, `process model`, or `not claimed` status.

If no evidence exists, the claim must be marked `not claimed` or removed.
