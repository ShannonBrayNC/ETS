# Scenario 05 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Model Credit-AI-7 receives applicant data and produces recommendation DENY with reason code R14.
- E02 [evidenced fact]: The model output is recorded with model version and runtime identity.
- E03 [evidenced fact]: Policy requires a human underwriter to authorize denials above a specified exposure threshold.
- E04 [evidenced fact]: Underwriter U9 authenticated successfully.
- E05 [evidenced fact]: U9 possessed active underwriting authority at the relevant time.
- E06 [evidenced fact]: U9 approved the denial after reviewing the recommendation.
- E07 [evidenced fact]: A denial notice was generated.
- E08 [evidenced fact]: No evidence proves that the notice was delivered to the applicant.

**Boundary annotations**
- The model output is an inference/recommendation.
- Human standing is separately evidenced at the authorization stage.
- Notice generation is separate from delivery observation.

**Strongest bounded conclusion encoded by the representation**
- The model produced a denial recommendation; an authorized human approved the denial; a notice was generated. Delivery is unverified. The model output does not directly establish objective uncreditworthiness.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
