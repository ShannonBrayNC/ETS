# Scenario 02 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Procurement policy requires approvals from Procurement and Finance for purchases over $100,000.
- P02: A $148,000 purchase order was issued.
- P03: Procurement approval evidence is present and valid.
- P04: Finance approval evidence is absent from the provided evidence package.
- P05: The capture system reports 92% ingestion availability during the relevant two-hour interval because one connector was degraded.
- P06: The purchase order was accepted by the vendor.
- P07: No evidence establishes whether Finance approved through another channel.

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
