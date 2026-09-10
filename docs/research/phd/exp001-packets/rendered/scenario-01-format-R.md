# Scenario 01 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Applicant record A-1042 was submitted at 09:14 on 3 March.
- D02 [domain fact]: Reviewer R17 authenticated using a valid agency credential.
- D03 [domain fact]: R17 was assigned the role Senior Reviewer in the directory at the time of action.
- D04 [domain fact]: The delegation permitting R17 to approve claims above $25,000 expired at 00:00 on 1 March.
- D05 [domain fact]: No replacement delegation is present in the evidence package.
- D06 [domain fact]: R17 approved a $31,500 claim at 10:02 on 3 March.
- D07 [domain fact]: The approval record is signed and its digest verifies.
- D08 [domain fact]: A downstream payment instruction was generated.
- D09 [domain fact]: No settlement confirmation is present.

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
