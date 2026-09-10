# Scenario 12 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: Ranger signing key K7 was valid at retained checkpoint C100.
- D02 [domain fact]: C100 is registry-signed and verifies.
- D03 [domain fact]: Authority history later revokes K7 at C104.
- D04 [domain fact]: A verifier is presented C100 plus a Ranger record signed by K7 after revocation.
- D05 [domain fact]: The presented C100 chain is internally valid but does not include C104.
- D06 [domain fact]: An independent retained authority head known to the verifier is C105.

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
