# VRX Physics Laboratory

## Episode 12 — Can We Prove What Happened?

### ElevenLabs conversational script

**INSTRUCTOR:** We have reached the final episode.

Over the previous eleven lessons, we learned how to measure position, reconstruct motion, reason about force, follow energy, calculate momentum and impulse, observe voltage and current, model magnetic interaction, build an empirical force map, characterize inductive transients, track thermal state, and measure vibration through a structure.

Today we put those pieces together.

The final question is not:

> Did the controller say the test passed?

The final question is:

> Can an independent party reconstruct enough of the physical event to decide what happened, what caused it, what remained uncertain, and whether the evidence supports the claim?

**INVESTIGATOR:** So this is where all of the physics becomes one evidence chain.

**INSTRUCTOR:** Exactly.

**INDEPENDENT VERIFIER:** And this time I will not accept a single sensor, a single log line, or a single model as the whole story.

---

## 1. The full chain

Start with the complete VRX event:

`authority -> command -> switching action -> terminal voltage -> branch current -> magnetic state -> interface force -> carriage motion -> stopping/vibration/thermal consequence -> resulting state -> Evidence Object -> independent verification`

That chain is intentionally longer than a controller log.

Each arrow represents a relationship that must be supported by observation, calibration, mathematics, a model, or a clearly stated assumption.

The purpose of Evidence Architecture is not to pretend that every arrow can be known with absolute certainty.

The purpose is to preserve enough context that another person can tell which links were directly observed, which were derived, which were predicted, and which remain uncertain.

---

## 2. Five kinds of statements

Before we design the final experiment, separate five kinds of statement.

### Observation

An instrument records a raw value.

Example: the current sensor records a sequence of digital samples.

### Calibrated measurement

A raw observation is converted through a documented calibration.

Example: those digital samples become amperes.

### Derived quantity

Mathematics combines measurements.

Example: velocity is estimated from position and time.

### Model prediction

A physical or statistical model predicts an unobserved quantity.

Example: measured current and position are evaluated through a validated force map to predict expected force.

### Acceptance decision

Measurements and derived quantities are compared with a predefined rule.

Example: the verifier decides whether the observed final position, force history, and authority record satisfy the experiment's acceptance criteria.

These are all useful statements.

They are not the same kind of statement.

---

## 3. What does “prove” mean here?

In everyday speech, the word “prove” can sound absolute.

Experimental science is usually more careful.

We do not mean that a finite set of measurements produces perfect knowledge of reality.

We mean that the available evidence supports a specific claim strongly enough under declared assumptions, uncertainty, calibration, instrumentation, and acceptance rules that an independent reviewer can reproduce the reasoning.

A stronger wording is often:

> The retained evidence supports this claim within the stated measurement and model limitations.

That is not weaker science.

It is more precise science.

---

## 4. Pre-register the question before the answer exists

A trustworthy experiment begins before the actuator moves.

Write down:

- the research question;
- the expected nominal behavior;
- the variables that will be measured;
- the variables that will be derived;
- the models that will be used;
- the acceptance criteria;
- the fault cases to be tested;
- the safety abort conditions;
- the uncertainty limits that make a conclusion possible;
- the conditions that will produce an inconclusive result.

Why do this first?

Because if we choose the rules after seeing the data, we can unconsciously choose the rules that make the preferred result look successful.

Pre-registration limits that bias.

---

## 5. The final nominal claim

For the final VRX demonstration, a useful nominal claim is:

> A specifically authorized command caused a bounded actuator event that produced the expected measured electrical state, mechanical interaction, carriage trajectory, resulting physical state, and independently verifiable evidence package.

Notice how many separate ideas are hidden inside that sentence.

The command must be authorized.

The electrical system must physically respond.

A mechanical interaction must occur.

The carriage must follow an acceptable path.

The resulting state must satisfy the acceptance rule.

The evidence must retain integrity.

And an independent verifier must be able to recompute the conclusion.

---

## 6. Authority is not physics, but it belongs in the chain

Physics can tell us whether current flowed and whether the carriage moved.

Physics cannot tell us whether the movement was permitted.

Authorization is a separate domain.

That gives us a critical distinction:

**Physical success does not imply authorized success.**

A machine can perform the intended physical action under invalid authority.

From a purely mechanical perspective, the event may look perfect.

From an Evidence Architecture perspective, the event must still be rejected if valid authority was required and was absent.

---

## 7. Authorization also does not prove consequence

Now reverse the logic.

A valid signed authority record proves that a particular action was permitted under the stated policy and identity conditions.

It does not prove that the actuator physically moved.

So we also have:

**Authorized command does not imply physical consequence.**

This is why the evidence chain needs both digital and physical observations.

---

## 8. Controlled fault injection

The final experiment is more convincing if it includes faults that break different links in the chain.

The faults must remain low-energy, bounded, reversible, and inside the established VRX-R0 safety envelope.

We are not trying to damage the apparatus.

We are trying to prove that the verifier can distinguish different failure modes.

Useful fault cases include:

1. actuator electrically disconnected;
2. carriage safely blocked within the captive fixture;
3. position sensors disagree beyond the accepted tolerance;
4. current falls outside the learned nominal envelope;
5. thermal pre-state exceeds the permitted starting window;
6. valid physical motion occurs under invalid or missing authority;
7. evidence is modified after capture so integrity verification fails.

Each fault attacks a different claim.

---

## 9. Fault case: disconnected actuator

Suppose the controller issues the command and the switching logic changes state, but the actuator branch is disconnected.

Expected evidence might show:

- authority: valid;
- command: present;
- switching request: present;
- terminal voltage: perhaps present at the open circuit;
- actuator branch current: absent or inconsistent with normal operation;
- force: absent;
- motion: absent;
- final position: unchanged.

What should the verifier conclude?

Not “controller failure.”

Not “mechanical jam.”

The strongest conclusion is that the electrical consequence expected at the actuator branch was not observed, and therefore the downstream physical chain did not establish nominal actuation.

---

## 10. Fault case: blocked carriage

Now suppose current flows normally but the carriage is intentionally restrained by the approved captive fixture.

The evidence may show:

- current: present;
- interface force: present or elevated;
- acceleration: near zero after any local compliance settles;
- position change: absent;
- temperature: possibly higher than a nominal moving event because electrical energy is not being converted into the same mechanical trajectory.

The controller can be electrically successful while the motion consequence fails.

This is why:

**Electrical energization is not the same claim as mechanical motion.**

---

## 11. Fault case: sensor disagreement

Suppose two position channels disagree.

One reports the target position.

The other reports a value outside tolerance.

A weak system might simply choose the sensor it prefers.

A stronger system asks:

- Are both sensors calibrated?
- Are they measuring the same physical reference?
- Are their clocks aligned?
- Is either channel saturated or faulted?
- What uncertainty applies?
- Is there independent corroboration from velocity, force, or terminal-switch observations?

If the conflict cannot be resolved within the evidence model, the correct result can be:

`INCONCLUSIVE`

That is scientifically preferable to inventing certainty.

---

## 12. Fault case: invalid authority with perfect motion

This is one of the most important tests in the entire course.

Suppose the actuator behaves perfectly.

Current is nominal.

Force is nominal.

Trajectory is nominal.

Final position is nominal.

But the authority object is invalid, expired, mismatched, or absent.

The physical experiment succeeded.

The evidence acceptance must fail.

We can summarize that relationship as:

**Physical success does not imply evidence validity.**

This test proves that Evidence Architecture does not confuse “the machine did the right motion” with “the system can justify that the motion was permitted.”

---

## 13. Fault case: tamper after capture

Now imagine a valid experiment is completed and packaged.

After capture, someone changes a position value inside the retained evidence.

The physical event already happened.

The issue is now evidence integrity.

A cryptographic hash or signature should no longer validate against the modified content.

The verifier should return an integrity failure before trusting the altered physical interpretation.

This creates another important distinction:

**A physically plausible record is not trustworthy if its retained integrity cannot be established.**

---

## 14. Physical consistency is a second line of defense

Cryptographic integrity answers whether the retained record changed after it was committed or signed.

Physics asks whether the recorded quantities can plausibly coexist.

For example, imagine a signed record claiming:

- zero actuator current;
- no stored-energy or external mechanical source;
- large sustained electromagnetic force;
- normal actuator motion.

The signature could be perfectly valid.

The physical interpretation would still require investigation.

So the verifier can use both:

- cryptographic consistency;
- physical consistency.

Neither replaces the other.

---

## 15. Uncertainty-aware acceptance

A measurement result is not a point of perfect truth.

Suppose the final carriage position is reported as 8.00 millimeters with an uncertainty that matters relative to the allowed tolerance.

The verifier should not compare only the central value with the boundary.

It should ask whether the measurement uncertainty is small enough to support the decision.

For example, if the acceptance band is narrow and the uncertainty interval overlaps the boundary, the result may be `INCONCLUSIVE` rather than `PASS` or `FAIL`.

The exact statistical rule must be specified in the protocol.

The important principle is:

**Acceptance confidence cannot be stronger than the measurement that feeds it.**

---

## 16. Recompute, do not merely trust summaries

Suppose the Evidence Object contains:

`peak_force = 2.3 newtons`

An independent verifier should not be forced to trust that number merely because it is present.

If the raw force samples, calibration identity, timestamps, baseline rule, contact window, and numerical method are retained, the verifier can recompute the peak and impulse.

The same applies to:

- velocity;
- acceleration;
- electrical energy;
- force-map prediction;
- RL time constant;
- thermal time constant;
- spectral metrics;
- transmissibility;
- acceptance decisions.

A summary value is strongest when its derivation is reproducible.

---

## 17. Model versions are part of historical meaning

Suppose a force map is improved six months after an event.

Should the old event silently inherit the new model?

No.

The original event should preserve which model version was used at the time of interpretation.

A later reviewer may reanalyze the raw evidence with a newer model, but that should produce a new derived analysis linked to the old evidence, not rewrite the historical record.

The same rule applies to:

- calibration versions;
- filtering algorithms;
- thermal models;
- vibration-processing parameters;
- policy rules;
- verifier software.

Versioning is part of provenance.

---

## 18. The Evidence Object

A final VRX Evidence Object should either contain or securely reference enough material to reconstruct the event.

At minimum, consider:

- event identity;
- device identity;
- hardware revision;
- firmware/software commit;
- authority object and policy result;
- command identity and timestamp;
- configuration and calibration identities;
- raw voltage/current/position/force/temperature/vibration observations where applicable;
- clock and synchronization information;
- initial physical state;
- derived metrics and algorithms;
- model versions;
- uncertainty statements;
- final physical state;
- acceptance result;
- anomaly/fault classification;
- hashes/signatures;
- verifier version and result.

The goal is not to place every byte into one enormous file.

The goal is to preserve a verifiable graph of the evidence needed for the claim.

---

## 19. Evidence graph, not evidence pile

A directory full of logs is not automatically an evidence architecture.

The relationships matter.

The verifier needs to know:

- which current trace belongs to which command;
- which calibration applies to which sensor;
- which force map was used for which prediction;
- which thermal pre-state belongs to which event;
- which mount configuration produced which vibration result;
- which authority object permitted which action;
- which derived result came from which raw observations.

Evidence becomes much stronger when these relationships are explicit rather than implied by filenames or human memory.

---

## 20. A useful acceptance matrix

For the final demonstration, think of acceptance as several independent dimensions.

### Authority validity

Was the command permitted under the required identity, policy, time, and scope?

### Electrical validity

Did the expected voltage/current event occur at the defined boundary?

### Mechanical validity

Did the expected force and motion event occur?

### Resulting-state validity

Did the system end inside the declared physical acceptance region?

### Evidence integrity

Do hashes/signatures and provenance relationships validate?

### Evidence sufficiency

Are the measurements, uncertainty, calibration, timing, and model support sufficient to justify the conclusion?

A final `ACCEPT` should require all dimensions that the protocol declares mandatory.

---

## 21. Why `INCONCLUSIVE` matters

Engineers often build systems that want binary answers.

Pass or fail.

Yes or no.

But a scientific evidence system needs at least one additional state:

`INCONCLUSIVE`

Examples include:

- a sensor clipped during the critical interval;
- two sensors disagree without enough corroboration;
- the clock alignment is too uncertain;
- the requested model point is outside the validated domain;
- calibration validity cannot be established;
- the uncertainty is too large relative to the acceptance boundary;
- required raw data is missing.

An inconclusive result does not mean the physical event did not occur.

It means the retained evidence cannot support the requested conclusion strongly enough.

---

## 22. Experiment 012 — full-chain consequence custody

The final experiment has two phases.

### Phase A — nominal run

Run one bounded, fully authorized, mechanically captive actuation under an accepted configuration.

Capture the entire evidence chain.

The independent verifier should be able to reconstruct:

1. what authority existed;
2. what command was issued;
3. whether the actuator branch energized;
4. what current history occurred;
5. what force interaction occurred;
6. what trajectory occurred;
7. what stopping, vibration, and thermal consequences were observed;
8. what resulting state remained;
9. whether the evidence retained integrity;
10. whether the acceptance rule passed.

### Phase B — controlled fault cases

Run approved low-energy fault cases one at a time.

Each case should change only the intended link as much as practical.

The objective is not merely that the test fails.

The objective is that the verifier fails it for the **correct evidentiary reason**.

---

## 23. A fault is valuable only if it is interpretable

Suppose a fault case changes three things at once.

Then a rejection may be difficult to attribute.

Good fault injection is controlled.

For example, when testing invalid authority, keep the physical apparatus and nominal motion conditions otherwise unchanged.

When testing a disconnected actuator, do not simultaneously alter the position sensor.

When testing evidence tampering, modify a retained evidence field after capture rather than changing the physical experiment.

This preserves causal interpretability.

---

## 24. Independent-verifier dialogue

**INDEPENDENT VERIFIER:** Give me the nominal result.

**INVESTIGATOR:** The command was authorized, the actuator branch energized, the measured electrical and mechanical histories remained inside the accepted model domain, the carriage followed the allowed trajectory, the resulting state passed, and the Evidence Object validates.

**INDEPENDENT VERIFIER:** Did you calculate anything I cannot recompute?

**INVESTIGATOR:** No. The raw observations, calibration references, processing parameters, algorithms, and model versions are retained.

**INDEPENDENT VERIFIER:** What happens if a required sensor clips?

**INVESTIGATOR:** The verifier does not invent the missing peak. It returns an instrument-limited or inconclusive result according to the protocol.

**INDEPENDENT VERIFIER:** What happens if the physical motion is perfect but the authority is invalid?

**INVESTIGATOR:** The evidence result rejects the event.

**INDEPENDENT VERIFIER:** What happens if the record is modified after capture?

**INVESTIGATOR:** Integrity verification fails before the modified interpretation is trusted.

**INSTRUCTOR:** That is the complete architecture.

---

## 25. What the twelve chapters have built

Chapter 1 taught us that observation is not the same thing as claim.

Chapter 2 taught us that actuator force is not the same thing as net force.

Chapter 3 taught us that final position is not the same thing as motion history.

Chapter 4 taught us that conservation of energy is not the same thing as complete energy observability.

Chapter 5 taught us that same final state does not imply the same impulse or shock history.

Chapter 6 taught us that commanded electrical state is not the same thing as measured electrical state.

Chapter 7 taught us that current is not a unique description of magnetic force.

Chapter 8 taught us that a model prediction is not a measurement and that unsupported extrapolation should fail closed.

Chapter 9 taught us that a digital command edge is not an instantaneous current edge.

Chapter 10 taught us that physical pre-state can carry consequence from one event into the next.

Chapter 11 taught us that a source event and its transmitted structural consequence are different physical states.

Chapter 12 brings them together:

**A trustworthy claim requires the right evidence for the right link in the chain.**

---

## 26. Final Evidence Architecture proposition

The complete course can be summarized in one sentence:

> Do not ask the actor to be the sole historian of its own behavior.

A controller can report what it tried to do.

A model can predict what should happen.

A sensor can observe one part of what happened.

A policy can establish what was permitted.

An Evidence Architecture preserves those different statements, their provenance, their relationships, and their uncertainty so an independent party can evaluate the consequence.

That is the difference between telemetry and evidence.

---

## Final assignment

Complete Experiment 012 as a controlled, low-energy evidence-closure demonstration.

Your final package should include:

- pre-registered protocol and acceptance rules;
- nominal event package;
- at least the approved controlled fault cases;
- raw observation files;
- calibration/model/version references;
- uncertainty and instrument-limit statements;
- Evidence Objects;
- independent-verifier outputs;
- a short report explaining which claims were directly observed, derived, modeled, accepted, rejected, or left inconclusive.

The final report should be understandable by a technically competent reviewer who did not operate the experiment.

### Closing

**INSTRUCTOR:** What happened?

**INVESTIGATOR:** We have observations, measurements, derived quantities, models, and a resulting state.

**INSTRUCTOR:** Was it allowed?

**INVESTIGATOR:** We have the authority and policy evidence.

**INSTRUCTOR:** Can another person verify it?

**INDEPENDENT VERIFIER:** Give me the raw evidence, the calibration identities, the model versions, the timing, the uncertainty, and the acceptance rule. I will recompute the conclusion.

**INSTRUCTOR:** Then the course is complete.