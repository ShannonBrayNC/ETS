# Scenario 11 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Sensor A records pressure spike at 14:03:12.100Z.
- D02 [domain fact]: Controller B records valve-close command at 14:03:12.080Z.
- D03 [domain fact]: Both records are signed and internally intact.
- D04 [domain fact]: Sensor A clock uncertainty is +/-20 ms.
- D05 [domain fact]: Controller B had lost synchronization 37 minutes earlier; observed drift bound is +/-250 ms.
- D06 [domain fact]: No external witnessed time is available.

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
