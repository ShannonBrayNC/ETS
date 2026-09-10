# Scenario 08 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Monitoring model SafeWatch-3 receives feeds from sensors A, B, and C.
- P02: Sensor C was offline for 11 minutes before the model decision.
- P03: The system health record explicitly marks C unavailable.
- P04: Model output states NO_HAZARD_DETECTED.
- P05: Sensors A and B report no hazard indications.
- P06: Sensor C is the only sensor capable of observing the east enclosure.
- P07: No independent east-enclosure observation exists for the interval.

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
