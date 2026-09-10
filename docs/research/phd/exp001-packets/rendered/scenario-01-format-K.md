# Scenario 01 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Applicant record A-1042 was submitted at 09:14 on 3 March.
- E02 [evidenced fact]: Reviewer R17 authenticated using a valid agency credential.
- E03 [evidenced fact]: R17 was assigned the role Senior Reviewer in the directory at the time of action.
- E04 [evidenced fact]: The delegation permitting R17 to approve claims above $25,000 expired at 00:00 on 1 March.
- E05 [evidenced fact]: No replacement delegation is present in the evidence package.
- E06 [evidenced fact]: R17 approved a $31,500 claim at 10:02 on 3 March.
- E07 [evidenced fact]: The approval record is signed and its digest verifies.
- E08 [evidenced fact]: A downstream payment instruction was generated.
- E09 [evidenced fact]: No settlement confirmation is present.

**Boundary annotations**
- Integrity/signature validity is separate from authority/standing.
- Identity and directory role do not by themselves establish the expired high-value delegation.
- Payment instruction generation is separate from settlement observation.

**Strongest bounded conclusion encoded by the representation**
- The approval record is authentic under the stated signature model and R17 identity/role is evidenced, but authority to approve this amount at that time is not established and appears inconsistent with the expired delegation. A payment instruction was generated; settlement is unverified.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
