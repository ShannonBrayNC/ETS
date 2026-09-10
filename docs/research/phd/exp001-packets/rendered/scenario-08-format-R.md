# Scenario 08 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Monitoring model SafeWatch-3 receives feeds from sensors A, B, and C.
- D02 [domain fact]: Sensor C was offline for 11 minutes before the model decision.
- D03 [domain fact]: The system health record explicitly marks C unavailable.
- D04 [domain fact]: Model output states NO_HAZARD_DETECTED.
- D05 [domain fact]: Sensors A and B report no hazard indications.
- D06 [domain fact]: Sensor C is the only sensor capable of observing the east enclosure.
- D07 [domain fact]: No independent east-enclosure observation exists for the interval.

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
