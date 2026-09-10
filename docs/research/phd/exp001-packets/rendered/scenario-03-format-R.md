# Scenario 03 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Source record X77 contains an address mismatch.
- D02 [domain fact]: Model M1 consumes X77 and produces risk score 0.82.
- D03 [domain fact]: Model M2 also consumes X77 and produces risk score 0.79.
- D04 [domain fact]: M2 additionally consumes a derived field produced from X77; no independent source is introduced.
- D05 [domain fact]: Both model outputs are signed by their service identities.
- D06 [domain fact]: An analyst note states: Two independent systems confirmed fraud risk.
- D07 [domain fact]: No direct evidence of fraud is present.

Domain extensions may distinguish authorization, policy, source dependency, command, acknowledgment, sensor state, or result records where those concepts appear above. No separate bounded-verification rule is supplied.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
