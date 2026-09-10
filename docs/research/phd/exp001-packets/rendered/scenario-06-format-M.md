# Scenario 06 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: An AI operations agent identifies an account as high risk.
- P02: Policy engine authorizes account suspension.
- P03: The agent issues disable-account to the identity service.
- P04: The identity service returns 202 Accepted with operation ID OP-88.
- P05: No completion event for OP-88 is present.
- P06: A later authentication attempt succeeds 90 seconds after the 202 Accepted response.
- P07: The authentication event is valid under the identity service's logging model.

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
