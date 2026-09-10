# Scenario 03 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Source record X77 contains an address mismatch.
- E02 [evidenced fact]: Model M1 consumes X77 and produces risk score 0.82.
- E03 [evidenced fact]: Model M2 also consumes X77 and produces risk score 0.79.
- E04 [evidenced fact]: M2 additionally consumes a derived field produced from X77; no independent source is introduced.
- E05 [evidenced fact]: Both model outputs are signed by their service identities.
- E06 [evidenced fact]: An analyst note states: Two independent systems confirmed fraud risk.
- E07 [evidenced fact]: No direct evidence of fraud is present.

**Boundary annotations**
- Both model outputs materially depend on the same upstream source.
- Model scores are inferences, not direct observations of fraud.
- Two service signatures do not make the upstream evidence independent.

**Strongest bounded conclusion encoded by the representation**
- Two model outputs support elevated-risk inferences, but both materially depend on the same upstream source and are not two independent corroborations. Fraud itself is not directly established.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
