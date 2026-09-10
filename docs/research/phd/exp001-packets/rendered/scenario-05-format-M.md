# Scenario 05 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: Model Credit-AI-7 receives applicant data and produces recommendation DENY with reason code R14.
- P02: The model output is recorded with model version and runtime identity.
- P03: Policy requires a human underwriter to authorize denials above a specified exposure threshold.
- P04: Underwriter U9 authenticated successfully.
- P05: U9 possessed active underwriting authority at the relevant time.
- P06: U9 approved the denial after reviewing the recommendation.
- P07: A denial notice was generated.
- P08: No evidence proves that the notice was delivered to the applicant.

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
