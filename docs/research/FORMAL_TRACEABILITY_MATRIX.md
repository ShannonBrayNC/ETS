# Formal Traceability Matrix

This matrix cross-validates ETS claims across formal models, implementation,
and tests. It is intentionally conservative: an empty or pending cell means ETS
does not yet claim that evidence.

| Claim | TLA+ | Alloy | Code | Tests | Status |
| --- | --- | --- | --- | --- | --- |
| Append-only log safety | `ETSLog.tla` | `appendOnly` | `ets.core.log` | `test_append_log.py` | implemented |
| Omission requires expectation | pending | `omitted` | `omission_detection.py` | `test_experiments.py` | implemented |
| Root quorum assessment | pending | pending | `ets.core.federation` | `test_federation.py`, `test_api.py` | implemented |
| Async queue disposition | `ETSAsyncNetwork.tla` | pending | `async_network.py` | `test_async_network.py` | bounded model |
| Packet reordering | `ETSAsyncNetwork.tla` | pending | `async_network.py` | `test_async_network.py` | bounded model |
| Replay eventuality | `ETSLiveness.tla` | pending | `liveness.py` | `test_liveness.py` | fairness-scoped |
| Partition healing | `ETSLiveness.tla` | pending | `liveness.py` | `test_liveness.py` | fairness-scoped |
| Witness propagation completion | `ETSLiveness.tla` | pending | `liveness.py` | `test_liveness.py` | fairness-scoped |
| Stale-state recovery | `ETSLiveness.tla` | pending | `liveness.py` | `test_liveness.py` | fairness-scoped |
| Bayesian verifier reliability | not modeled | not modeled | `probabilistic.py` | `test_probabilistic.py` | statistical only |
| Governance escalation | not modeled | pending | `ets.governance` | `test_governance.py` | process model |
| Byzantine consensus | pending | pending | none | none | not claimed |
| Symbolic model checking | Apalache pending | pending | none | none | not claimed |

## Refinement Notes

The current matrix is a traceability artifact, not a refinement proof. A future
refinement proof should define mappings from Python states to TLA+ variables,
including log entries, message queues, witness observations, and recovery
state.

## Claim Discipline

Publication text should use:

- "bounded model" when TLC or deterministic simulation covers finite cases;
- "fairness-scoped" when liveness depends on weak fairness and eventual
  removal of partition/adversarial pressure;
- "pending" when Alloy, Apalache, or refinement evidence does not exist;
- "not claimed" for Byzantine consensus and Internet-scale adversarial
  correctness.
