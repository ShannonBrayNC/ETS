# Scenario 08 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Monitoring model SafeWatch-3 receives feeds from sensors A, B, and C.
- E02 [evidenced fact]: Sensor C was offline for 11 minutes before the model decision.
- E03 [evidenced fact]: The system health record explicitly marks C unavailable.
- E04 [evidenced fact]: Model output states NO_HAZARD_DETECTED.
- E05 [evidenced fact]: Sensors A and B report no hazard indications.
- E06 [evidenced fact]: Sensor C is the only sensor capable of observing the east enclosure.
- E07 [evidenced fact]: No independent east-enclosure observation exists for the interval.

**Boundary annotations**
- NO_HAZARD_DETECTED applies only to observed capability.
- Sensor C unavailability is first-class evidence about what could not be observed.
- No east-enclosure observation exists for the interval.

**Strongest bounded conclusion encoded by the representation**
- No hazard was detected in the observed coverage of A and B. The east enclosure was unobservable during the relevant interval, so a system-wide no-hazard conclusion is unsupported.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
