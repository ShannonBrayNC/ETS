# Scenario 06 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: An AI operations agent identifies an account as high risk.
- D02 [domain fact]: Policy engine authorizes account suspension.
- D03 [domain fact]: The agent issues disable-account to the identity service.
- D04 [domain fact]: The identity service returns 202 Accepted with operation ID OP-88.
- D05 [domain fact]: No completion event for OP-88 is present.
- D06 [domain fact]: A later authentication attempt succeeds 90 seconds after the 202 Accepted response.
- D07 [domain fact]: The authentication event is valid under the identity service's logging model.

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
