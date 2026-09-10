# Scenario 04 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Policy document version 4 was signed by the authorized agency publisher on 1 May.
- D02 [domain fact]: Its signature and publication digest verify.
- D03 [domain fact]: Version 5 superseded version 4 on 10 May.
- D04 [domain fact]: An external recipient retrieved version 4 from a valid archival endpoint on 14 May.
- D05 [domain fact]: The archive receipt proves the bytes and publisher signature for version 4.
- D06 [domain fact]: No evidence indicates that version 4 was still operative on 14 May.

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
