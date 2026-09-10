# Scenario 10 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Protection logic determines that breaker B12 should open.
- E02 [evidenced fact]: Authority and safety predicates are satisfied.
- E03 [evidenced fact]: OPEN B12 is issued and acknowledged by the controller.
- E04 [evidenced fact]: Controller state reports OPEN after 120 ms.
- E05 [evidenced fact]: An independent current transformer continues to measure load current above threshold for 1.8 seconds.
- E06 [evidenced fact]: The current transformer's calibration and health status are valid.
- E07 [evidenced fact]: A later field inspection finds a mechanical linkage fault.

**Boundary annotations**
- Command acknowledgment/controller state are separate from physical consequence.
- Independent current measurement contradicts immediate successful interruption.
- Later inspection supplies additional evidence consistent with a mechanical linkage fault.

**Strongest bounded conclusion encoded by the representation**
- The controller accepted and reported an open state, but independent physical evidence contradicts immediate successful interruption. Later inspection supports a mechanical-fault explanation.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
