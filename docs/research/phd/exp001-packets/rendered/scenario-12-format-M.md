# Scenario 12 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Ranger signing key K7 was valid at retained checkpoint C100.
- P02: C100 is registry-signed and verifies.
- P03: Authority history later revokes K7 at C104.
- P04: A verifier is presented C100 plus a Ranger record signed by K7 after revocation.
- P05: The presented C100 chain is internally valid but does not include C104.
- P06: An independent retained authority head known to the verifier is C105.

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
