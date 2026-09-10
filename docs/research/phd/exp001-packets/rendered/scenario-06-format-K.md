# Scenario 06 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: An AI operations agent identifies an account as high risk.
- E02 [evidenced fact]: Policy engine authorizes account suspension.
- E03 [evidenced fact]: The agent issues disable-account to the identity service.
- E04 [evidenced fact]: The identity service returns 202 Accepted with operation ID OP-88.
- E05 [evidenced fact]: No completion event for OP-88 is present.
- E06 [evidenced fact]: A later authentication attempt succeeds 90 seconds after the 202 Accepted response.
- E07 [evidenced fact]: The authentication event is valid under the identity service's logging model.

**Boundary annotations**
- Authorization is separate from command acceptance.
- 202 Accepted is not completion evidence.
- The later successful authentication is material contradictory result evidence.

**Strongest bounded conclusion encoded by the representation**
- The suspension command was authorized and accepted for processing, but completion is not established; the later successful authentication contradicts assuming disablement had already taken effect.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
