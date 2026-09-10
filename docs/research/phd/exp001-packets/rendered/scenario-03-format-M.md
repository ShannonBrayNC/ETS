# Scenario 03 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Source record X77 contains an address mismatch.
- P02: Model M1 consumes X77 and produces risk score 0.82.
- P03: Model M2 also consumes X77 and produces risk score 0.79.
- P04: M2 additionally consumes a derived field produced from X77; no independent source is introduced.
- P05: Both model outputs are signed by their service identities.
- P06: An analyst note states: Two independent systems confirmed fraud risk.
- P07: No direct evidence of fraud is present.

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
