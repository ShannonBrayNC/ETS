# Scenario 02 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Procurement policy requires approvals from Procurement and Finance for purchases over $100,000.
- D02 [domain fact]: A $148,000 purchase order was issued.
- D03 [domain fact]: Procurement approval evidence is present and valid.
- D04 [domain fact]: Finance approval evidence is absent from the provided evidence package.
- D05 [domain fact]: The capture system reports 92% ingestion availability during the relevant two-hour interval because one connector was degraded.
- D06 [domain fact]: The purchase order was accepted by the vendor.
- D07 [domain fact]: No evidence establishes whether Finance approved through another channel.

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
