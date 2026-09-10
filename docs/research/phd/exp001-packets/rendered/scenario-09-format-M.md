# Scenario 09 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Ranger is in teleoperation mode.
- P02: Operator identity and motion authority are valid.
- P03: A forward-motion request for 1.0 m/s is issued.
- P04: Safety controller accepts the command.
- P05: Motor controller reports non-zero output current.
- P06: Wheel-encoder telemetry is absent because the encoder channel is degraded.
- P07: No independent position change observation is present.

Relationship interpretation follows ordinary provenance semantics. No additional verifier rule is supplied beyond the represented records and relationships.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
