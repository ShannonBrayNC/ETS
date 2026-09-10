# Scenario 07 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: A camera signs a capture artifact using a registered device key.
- E02 [evidenced fact]: The artifact bytes match the signed digest.
- E03 [evidenced fact]: An AI synthetic-media detector produces score 0.91 for likely synthetic.
- E04 [evidenced fact]: Detector version and threshold are known.
- E05 [evidenced fact]: Independent review finds no additional source artifact proving whether content was staged, generated, or merely post-processed.
- E06 [evidenced fact]: The camera signature proves capture provenance under the device trust model.

**Boundary annotations**
- Capture provenance is separate from scene truth.
- The detector score is an inference with known version/threshold.
- No evidence resolves whether the content was staged, generated, or post-processed.

**Strongest bounded conclusion encoded by the representation**
- The artifact is cryptographically linked to the registered capture device; the detector produced a strong synthetic-media inference. Neither mechanism alone proves scene truth or complete origin history.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
