# Scenario 07 — Format R

## Evidence representation

**Domain-extended provenance representation**

The same factual record is represented with domain-specific relationship types and state labels:
- D01 [domain fact]: A camera signs a capture artifact using a registered device key.
- D02 [domain fact]: The artifact bytes match the signed digest.
- D03 [domain fact]: An AI synthetic-media detector produces score 0.91 for likely synthetic.
- D04 [domain fact]: Detector version and threshold are known.
- D05 [domain fact]: Independent review finds no additional source artifact proving whether content was staged, generated, or merely post-processed.
- D06 [domain fact]: The camera signature proves capture provenance under the device trust model.

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
