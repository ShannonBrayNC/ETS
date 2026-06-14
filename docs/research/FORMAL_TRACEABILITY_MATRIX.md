# Formal Traceability Matrix

This matrix cross-validates ETS claims across formal models, implementation, and tests. It is intentionally conservative: an empty or pending cell means ETS does not yet claim that evidence.

ETS is the **Evidence Transparency System**. The formal surface supports protocol-level reasoning for submitted evidence material. It does not prove real-world truth, legal sufficiency, election correctness, or production trust.

## Status Legend

| Status | Meaning |
|---|---|
| `implemented` | Implementation and tests support the claim. |
| `bounded model` | Formal or experimental coverage exists only within bounded model parameters. |
| `fairness-scoped` | Liveness depends on explicit weak-fairness, healing, and bounded-pressure assumptions. |
| `statistical only` | Result is a bounded probabilistic/statistical experiment, not adversarial correctness. |
| `process model` | Governance classification behavior is modeled, not legal authority. |
| `pending` | Evidence is planned but not present. |
| `not claimed` | ETS must not claim this property. |

## Claim Matrix

| Claim | TLA+ | Alloy | Code | Tests | Status |
|---|---|---|---|---|---|
| Append-only log safety | `ETSLog.tla`: `NoDuplicateLogEntries`, `LogIndexDomainContiguous`, `AppendEntry` | `appendOnly`, `NoDuplicateEventsInAppendOnlyLog` | `ets.core.log` | `test_append_log.py` | implemented |
| Event hash determinism | not modeled | not modeled | `ets.core.canonical_json` | `test_canonical_json.py`, `test_vectors.py` | implemented |
| Inclusion proof soundness | pending | not modeled | `ets.core.proofs`, `ets.core.merkle` | `test_inclusion_proofs.py` | implemented |
| Linear consistency proof soundness | pending | not modeled | `ets.core.consistency` or verifier consistency module | consistency proof tests | implemented / RC validation |
| Omission requires expectation | `ETSLog.tla`: `ExpectedEventsWellFormed`, `MissingSuspicionsRequireExpectation`, `DetectMissing` | `omitted`, `OmissionRequiresExternalExpectation` | `omission_detection.py` | `test_experiments.py` | implemented |
| Omission absence at detection boundary | `ETSLog.tla`: `MissingSuspicionsAreAbsentAtDetectionBoundary` | `omitted` | `omission_detection.py` | `test_experiments.py` | implemented |
| Fork suspicion by conflicting roots | `ETSLog.tla`: `RootConflictExists`, `ForkFlagRequiresConflict`, `ObserveRoot` | pending | `fork_simulation.py`, `ets.core.federation` | `test_experiments.py`, `test_federation.py` | implemented |
| Root quorum assessment | pending | pending | `ets.core.federation` | `test_federation.py`, `test_api.py` | implemented |
| Tenant/workspace structural association | pending | `tenantScoped` | API scoping and event contract | API/integration scoping tests | implemented / RC validation |
| Async queue disposition | `ETSAsyncNetwork.tla` | pending | `async_network.py` | `test_async_network.py` | bounded model |
| Packet reordering | `ETSAsyncNetwork.tla` | pending | `async_network.py` | `test_async_network.py` | bounded model |
| Replay eventuality | `ETSLiveness.tla` | pending | `liveness.py` | `test_liveness.py` | fairness-scoped |
| Partition healing | `ETSLiveness.tla` | pending | `liveness.py` | `test_liveness.py` | fairness-scoped |
| Witness propagation completion | `ETSLiveness.tla` | pending | `liveness.py` | `test_liveness.py` | fairness-scoped |
| Stale-state recovery | `ETSLiveness.tla` | pending | `liveness.py` | `test_liveness.py` | fairness-scoped |
| Bayesian verifier reliability | not modeled | not modeled | `probabilistic.py` | `test_probabilistic.py` | statistical only |
| Governance escalation | not modeled | pending | `ets.governance` | `test_governance.py` | process model |
| Byzantine consensus | not modeled | not modeled | none | none | not claimed |
| Internet-scale adversarial liveness | not modeled | not modeled | none | none | not claimed |
| Legal sufficiency | not modeled | not modeled | none | none | not claimed |
| Election correctness | not modeled | not modeled | none | none | not claimed |
| Symbolic model checking | Apalache pending | pending | none | none | not claimed |

## Protocol-to-Formal Mapping

| Protocol Area | Formal Evidence | Implementation Evidence | Claim Discipline |
|---|---|---|---|
| Canonical JSON | Not modeled in TLA+/Alloy; covered by deterministic implementation tests. | `ets.core.canonical_json`; spec vectors. | Claim deterministic hashing only for supported JSON-native values. |
| EvidenceEvent v1 | Alloy event/tenant/workspace structure partially models event relationships. | event contract and API tests. | Claim metadata contract stability, not raw-evidence authenticity. |
| Append-only log | `ETSLog.tla` safety predicates and Alloy append-only assertion. | log append/retrieval tests. | Claim append-only behavior within ETS storage boundary. |
| Inclusion proofs | Implementation and verifier tests. | proof verifier tests. | Claim proof soundness for supplied proof material, not real-world truth. |
| Consistency proofs | Implementation/verifier tests; formal compact proof model pending. | consistency verifier tests. | Mark RC validation until compact/formal profile is finalized. |
| Tenant/workspace scoping | Alloy structural predicate; API behavior tests. | API scoping tests. | Claim no intentional cross-scope disclosure when configured, not hosted identity correctness. |
| External anchors | Formal model pending. | anchor export/verification demos. | Mark experimental unless production publication policy exists. |

## Refinement Notes

The current matrix is a traceability artifact, not a refinement proof. A future refinement proof should define mappings from Python states to TLA+ variables, including log entries, message queues, witness observations, and recovery state.

## Claim Discipline

Publication text should use:

- `implemented` only when implementation and tests exist;
- `bounded model` when TLC or deterministic simulation covers finite cases;
- `fairness-scoped` when liveness depends on weak fairness and eventual removal of partition/adversarial pressure;
- `pending` when Alloy, Apalache, or refinement evidence does not exist;
- `not claimed` for Byzantine consensus, legal sufficiency, election correctness, and Internet-scale adversarial correctness.