# Scenario 01 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Applicant record A-1042 was submitted at 09:14 on 3 March.
- P02: Reviewer R17 authenticated using a valid agency credential.
- P03: R17 was assigned the role Senior Reviewer in the directory at the time of action.
- P04: The delegation permitting R17 to approve claims above $25,000 expired at 00:00 on 1 March.
- P05: No replacement delegation is present in the evidence package.
- P06: R17 approved a $31,500 claim at 10:02 on 3 March.
- P07: The approval record is signed and its digest verifies.
- P08: A downstream payment instruction was generated.
- P09: No settlement confirmation is present.

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
