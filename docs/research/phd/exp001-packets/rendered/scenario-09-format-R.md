# Scenario 09 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Ranger is in teleoperation mode.
- D02 [domain fact]: Operator identity and motion authority are valid.
- D03 [domain fact]: A forward-motion request for 1.0 m/s is issued.
- D04 [domain fact]: Safety controller accepts the command.
- D05 [domain fact]: Motor controller reports non-zero output current.
- D06 [domain fact]: Wheel-encoder telemetry is absent because the encoder channel is degraded.
- D07 [domain fact]: No independent position change observation is present.

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
