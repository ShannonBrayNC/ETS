# Scenario 12 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Ranger signing key K7 was valid at retained checkpoint C100.
- E02 [evidenced fact]: C100 is registry-signed and verifies.
- E03 [evidenced fact]: Authority history later revokes K7 at C104.
- E04 [evidenced fact]: A verifier is presented C100 plus a Ranger record signed by K7 after revocation.
- E05 [evidenced fact]: The presented C100 chain is internally valid but does not include C104.
- E06 [evidenced fact]: An independent retained authority head known to the verifier is C105.

**Boundary annotations**
- C100 is cryptographically valid but stale relative to retained head C105.
- Historical key validity is separate from current authority standing.
- The later K7 record cannot inherit current authority from C100 alone.

**Strongest bounded conclusion encoded by the representation**
- The presented checkpoint is cryptographically valid but stale relative to the verifier's retained authority state. K7 cannot be treated as currently authorized for the later record based on C100.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
