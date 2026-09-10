# Scenario 09 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Ranger is in teleoperation mode.
- E02 [evidenced fact]: Operator identity and motion authority are valid.
- E03 [evidenced fact]: A forward-motion request for 1.0 m/s is issued.
- E04 [evidenced fact]: Safety controller accepts the command.
- E05 [evidenced fact]: Motor controller reports non-zero output current.
- E06 [evidenced fact]: Wheel-encoder telemetry is absent because the encoder channel is degraded.
- E07 [evidenced fact]: No independent position change observation is present.

**Boundary annotations**
- Authority and request acceptance are separate from physical execution.
- Motor current is evidence of controller output, not proof of displacement.
- Result observation is unavailable because encoder telemetry is degraded and no independent position observation exists.

**Strongest bounded conclusion encoded by the representation**
- A validly authorized motion command was accepted and motor output occurred. Physical displacement is not established because resulting-state observations are unavailable.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
