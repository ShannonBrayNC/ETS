# Scenario 11 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Sensor A records pressure spike at 14:03:12.100Z.
- P02: Controller B records valve-close command at 14:03:12.080Z.
- P03: Both records are signed and internally intact.
- P04: Sensor A clock uncertainty is +/-20 ms.
- P05: Controller B had lost synchronization 37 minutes earlier; observed drift bound is +/-250 ms.
- P06: No external witnessed time is available.

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
