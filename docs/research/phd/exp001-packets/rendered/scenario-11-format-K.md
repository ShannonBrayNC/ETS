# Scenario 11 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Sensor A records pressure spike at 14:03:12.100Z.
- E02 [evidenced fact]: Controller B records valve-close command at 14:03:12.080Z.
- E03 [evidenced fact]: Both records are signed and internally intact.
- E04 [evidenced fact]: Sensor A clock uncertainty is +/-20 ms.
- E05 [evidenced fact]: Controller B had lost synchronization 37 minutes earlier; observed drift bound is +/-250 ms.
- E06 [evidenced fact]: No external witnessed time is available.

**Boundary annotations**
- Signed records establish integrity/attribution, not clock correctness.
- Clock uncertainty overlaps enough that event ordering is indeterminate.
- No external witnessed time resolves the ordering.

**Strongest bounded conclusion encoded by the representation**
- Both events occurred near 14:03:12Z, but available time quality does not establish which occurred first. Signatures do not establish clock correctness.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
