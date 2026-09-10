# Scenario 05 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Model Credit-AI-7 receives applicant data and produces recommendation DENY with reason code R14.
- D02 [domain fact]: The model output is recorded with model version and runtime identity.
- D03 [domain fact]: Policy requires a human underwriter to authorize denials above a specified exposure threshold.
- D04 [domain fact]: Underwriter U9 authenticated successfully.
- D05 [domain fact]: U9 possessed active underwriting authority at the relevant time.
- D06 [domain fact]: U9 approved the denial after reviewing the recommendation.
- D07 [domain fact]: A denial notice was generated.
- D08 [domain fact]: No evidence proves that the notice was delivered to the applicant.

Domain extensions may distinguish authorization, policy, source dependency, command, acknowledgment, sensor state, or result records where those concepts appear above. No separate bounded-verification rule is supplied.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
