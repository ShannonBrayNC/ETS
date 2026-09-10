# Scenario 07 — Format M

## Evidence representation

**Provenance-oriented representation**

The following entities, activities, agents, records, and temporal facts are present in the provenance bundle:
- P01: A camera signs a capture artifact using a registered device key.
- P02: The artifact bytes match the signed digest.
- P03: An AI synthetic-media detector produces score 0.91 for likely synthetic.
- P04: Detector version and threshold are known.
- P05: Independent review finds no additional source artifact proving whether content was staged, generated, or merely post-processed.
- P06: The camera signature proves capture provenance under the device trust model.

Relationship interpretation follows ordinary provenance semantics. No additional verifier rule is supplied beyond the represented records and relationships.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
