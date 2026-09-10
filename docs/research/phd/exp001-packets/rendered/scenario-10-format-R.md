# Scenario 10 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Protection logic determines that breaker B12 should open.
- D02 [domain fact]: Authority and safety predicates are satisfied.
- D03 [domain fact]: OPEN B12 is issued and acknowledged by the controller.
- D04 [domain fact]: Controller state reports OPEN after 120 ms.
- D05 [domain fact]: An independent current transformer continues to measure load current above threshold for 1.8 seconds.
- D06 [domain fact]: The current transformer's calibration and health status are valid.
- D07 [domain fact]: A later field inspection finds a mechanical linkage fault.

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
