# Scenario 10 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Protection logic determines that breaker B12 should open.
- P02: Authority and safety predicates are satisfied.
- P03: OPEN B12 is issued and acknowledged by the controller.
- P04: Controller state reports OPEN after 120 ms.
- P05: An independent current transformer continues to measure load current above threshold for 1.8 seconds.
- P06: The current transformer's calibration and health status are valid.
- P07: A later field inspection finds a mechanical linkage fault.

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
