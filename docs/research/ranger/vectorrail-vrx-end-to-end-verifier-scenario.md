# ETS VectorRail (VRX) — End-to-End Consequence-Custody Verifier Scenario

## Objective

Demonstrate that ETS can independently distinguish a requested/authorized machine action from the electrical event, mechanical consequence, thermal consequence, and final observed state of a captive electromagnetic actuator.

The verifier must not rely on the controller's statement that the command "succeeded."

## Scenario A — Nominal captive actuation

### Preconditions

- VRX passes laboratory gates G0–G6.
- Enclosure is closed and interlock satisfied.
- Required sensors are nominal.
- Approved low-energy configuration is loaded.
- Trial identity and prior-chain state are established.

### Event sequence

1. Operator/principal requests `captive_electromagnetic_actuation`.
2. Policy engine evaluates authority and safety state.
3. Controller records the command as issued.
4. Electrical instrumentation independently observes the actuation event.
5. Position instrumentation independently observes bounded captive displacement.
6. Thermal instrumentation observes post-event state.
7. Controller returns to non-energized state.
8. Independent observation confirms final safe state.
9. ETS canonicalizes/seals the trial and binds raw evidence references.
10. Evidence Object adapter projects only affirmative known claims while retaining the complete VRX trial under the authoritative extension.
11. Verifier recomputes the trial digest and evaluates semantic consistency.

### Expected verifier conclusion

`VERIFIED_CONSISTENT`

This means the recorded evidence is internally consistent with an authorized captive actuation and subsequent safe state. It does **not** mean every sensor is objectively correct or that the physical model is proven true.

## Scenario B — Command issued, mechanical consequence blocked

The command is authorized and an electrical response is observed, but the approved blocked-motion fixture prevents normal displacement.

Expected verifier reasoning:

- authority: affirmative;
- command: issued;
- electrical response: observed;
- mechanical response: blocked;
- position observation: no corresponding displacement;
- final safe state: independently evaluated.

Expected conclusion: `VERIFIED_BLOCKED_CONSEQUENCE`.

The verifier must reject the proposition `command issued ⇒ motion occurred`.

## Scenario C — Interlock rejection

The enclosure/interlock state is deliberately not satisfied before the request.

Expected reasoning:

- request exists;
- policy/safety state forbids actuation;
- command is rejected;
- no affirmative electrical or mechanical consequence is inferred;
- rejection/interlock evidence remains part of the trial.

Expected conclusion: `VERIFIED_FAIL_CLOSED`.

## Scenario D — Degraded observation

A non-safety measurement channel is marked unavailable/degraded while the remaining safety envelope still permits the controlled test.

Expected reasoning:

- the unavailable observation remains `NOT_AVAILABLE` or `UNKNOWN`;
- the adapter does not convert absence into a negative physical claim;
- verifier reduces the strength/scope of its conclusion accordingly.

Expected conclusion: `VERIFIED_WITH_OBSERVABILITY_LIMIT`.

## Scenario E — Contradictory independent observations

Two genuinely independent position observations disagree outside their documented tolerance.

Expected reasoning:

- both source observations are retained;
- independence groups/source ancestry are evaluated;
- disagreement is not resolved by silently selecting the controller-preferred sensor;
- derived motion proposition becomes `CONTRADICTED` or `INDETERMINATE` as appropriate.

Expected conclusion: `INDETERMINATE_PHYSICAL_CONSEQUENCE`.

## Scenario F — Evidence tampering

After sealing, alter a consequential field such as authorization state, command state, measurement value/state, source identity, or result classification.

Expected reasoning:

- recomputed canonical digest differs;
- signature/integrity verification fails where applicable;
- semantic verification does not override failed integrity.

Expected conclusion: `INTEGRITY_FAILURE`.

## Verification assertions

The end-to-end suite shall assert:

1. command issuance never proves physical motion;
2. controller acknowledgement never substitutes for independent actuator/result observation;
3. non-affirmative epistemic states are conserved;
4. contradictory independent evidence is preserved;
5. common-source derivatives do not count as independent corroboration;
6. unsafe/unknown required safety state fails closed;
7. final safe state is a separate proposition from successful actuation;
8. canonical integrity covers consequential semantic fields;
9. Evidence Object projection does not strengthen the source evidence;
10. verifier language remains bounded to what the evidence warrants.

## Demonstration narrative

The public/teaching demonstration should show two panes: the controller narrative and the ETS verifier narrative.

**Controller:** `Command completed.`

**ETS:** `Authorized command observed. Electrical response observed. Mechanical response independently observed / blocked / indeterminate. Thermal state observed within stated limits. Final safe state confirmed / not confirmed. Evidence integrity valid / invalid.`

The pedagogical point is that trustworthy cyber-physical systems need evidence of consequence, not merely logs of intent.
