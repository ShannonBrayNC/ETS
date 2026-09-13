# Chapter 12 — Can We Prove What Happened?

**INSTRUCTOR:** We have reached the final chapter.

Over eleven chapters, we learned how to measure position, reconstruct motion, reason about force, follow energy, calculate momentum and impulse, observe voltage and current, model magnetic interaction, build a force map, characterize inductive transients, track thermal state, and measure vibration through a structure.

Now we put everything together.

The final question is not:

> Did the controller say the test passed?

The final question is:

> Can an independent party reconstruct enough of the event to decide what physically happened, what was authorized, what remained uncertain, and whether the evidence actually supports the claim?

**INVESTIGATOR:** So this is where physics becomes a complete evidence chain.

**INSTRUCTOR:** Exactly.

**INDEPENDENT VERIFIER:** And this time, no single log line, sensor, model, or signature gets to tell the whole story by itself.

---

## The complete chain

A full VRX event can be represented as:

`authority -> command -> switching action -> terminal voltage -> branch current -> magnetic interaction -> mechanical force -> carriage motion -> stopping, vibration, and thermal consequence -> resulting state -> Evidence Object -> independent verification`

That chain is much longer than a controller log.

Each arrow represents a relationship that has to be supported in some way.

Some links are directly observed.

Some are calibrated measurements.

Some are mathematically derived.

Some depend on a physical model.

Some come from authorization and policy rather than physics.

The purpose of Evidence Architecture is not to pretend that every link can be known with absolute certainty.

The purpose is to preserve enough information that another person can tell **which kind of statement each link represents and how strongly it is supported**.

---

## Observation, measurement, derivation, model, decision

Before we design the final experiment, separate five kinds of statement.

**Observation** is what an instrument or system directly recorded.

A current sensor produces raw samples. A position sensor produces raw readings. An accelerometer produces digitized acceleration channels.

**Calibrated measurement** is an observation converted into physical units through a documented calibration.

Raw counts become amperes, millimeters, newtons, or meters per second squared.

**Derived quantity** is calculated from measurements.

Velocity derived from position and time is an example. Impulse derived from a force-time integral is another.

**Model prediction** uses a model to infer something not directly observed.

A force predicted from measured current and position using the validated force map is a model prediction.

**Acceptance decision** compares the evidence with a predefined rule.

The rule might say that authority must be valid, current must lie inside an accepted envelope, trajectory must remain within limits, and final position must satisfy the terminal tolerance.

These statements can all appear in the same Evidence Object.

They must not be mislabeled as the same kind of evidence.

---

## What does “prove” mean in experimental engineering?

The word **prove** can sound absolute.

Mathematical proof and experimental evidence are not the same thing.

A finite experiment does not provide omniscient knowledge of the physical world.

In this book, a strong proof claim means something more disciplined:

> The retained evidence supports a specific conclusion strongly enough, under stated calibration, uncertainty, instrumentation, model, and acceptance assumptions, that an independent reviewer can reproduce the reasoning.

That is why a phrase such as “the evidence supports the claim within the stated limits” is often scientifically stronger than an unqualified declaration of certainty.

Uncertainty is not weakness.

Unstated uncertainty is weakness.

---

## Pre-register the question before seeing the answer

A trustworthy final experiment begins before the actuator moves.

Write down:

- the research question;
- expected nominal behavior;
- measurement channels;
- derived quantities;
- model versions;
- acceptance rules;
- fault cases;
- safety abort conditions;
- uncertainty limits;
- instrument-limit conditions;
- and the situations that will produce an inconclusive result.

Why do this first?

Because rules chosen after seeing the data can drift toward the result we prefer.

Pre-registration reduces that bias.

---

## The nominal claim

A useful full-chain claim is:

> A specifically authorized command caused a bounded VRX actuator event that produced the expected measured electrical state, mechanical interaction, carriage trajectory, resulting physical state, and independently verifiable evidence package.

That one sentence contains several separate claims.

The command was authorized.

The actuator branch physically energized.

A mechanical interaction occurred.

The carriage followed an acceptable trajectory.

The terminal and structural consequences remained within the declared rules.

The resulting state passed.

The evidence retained integrity.

An independent verifier can recompute the conclusion.

A strong test should be able to fail those claims independently.

---

## Authority is not physics

Physics can tell us whether current flowed and whether the carriage moved.

Physics cannot tell us whether the movement was permitted.

Authorization belongs to a different domain.

Suppose the carriage performs a perfectly nominal movement, but the command came from an invalid authority object.

The physical event succeeded.

The evidence acceptance should still fail if valid authority was required.

This gives us an important proposition:

**Physical success does not imply evidence validity.**

---

## Authorization does not prove physical consequence either

Now reverse the logic.

Suppose a valid authority record exists and the command is properly signed.

Does that prove the carriage moved?

No.

The actuator could be disconnected. The switching device could fail. The carriage could be blocked. A sensor could fail.

A valid authorization proves permission under the declared policy conditions.

It does not prove the downstream physical event happened.

So:

**Authorized command does not imply physical consequence.**

Control and evidence are complementary planes.

---

## Why controlled fault injection matters

A nominal run tells us that the system can produce an acceptable event.

Fault injection asks whether the verifier can tell **why** an event is unacceptable.

The faults in this course remain bounded, low-energy, reversible, and inside the mechanically captive VRX-R0 safety envelope.

We are not trying to break the apparatus.

We are trying to break different links in the evidence chain one at a time.

Useful cases include:

- actuator disconnected;
- carriage safely blocked;
- position channels disagree;
- current outside the validated envelope;
- thermal starting state outside the accepted window;
- physically nominal motion under invalid authority;
- post-capture evidence modification.

Each fault tests a different proposition.

---

## Fault case: actuator disconnected

Suppose authority is valid and the controller issues the correct command, but the actuator branch is electrically disconnected.

What might we observe?

The command exists.

The switching request exists.

A voltage may appear at the open circuit.

But normal actuator branch current does not appear.

Without current, the expected magnetic interaction does not develop.

Force and motion are absent.

The final position remains unchanged.

The strongest verifier conclusion is not simply “actuation failed.”

It is more specific:

> The expected electrical consequence at the actuator branch was not observed, so the downstream nominal physical chain was not established.

That is evidence localization.

---

## Fault case: current flows but the carriage is blocked

Now suppose the actuator is energized normally while the carriage is safely restrained by the approved captive fixture.

The evidence may show:

- valid authority;
- normal terminal voltage;
- normal or elevated current;
- mechanical force;
- little or no carriage displacement;
- possibly different thermal behavior because the mechanical trajectory changed.

The electrical subsystem physically responded.

The intended motion did not occur.

This demonstrates:

**electrical energization is not the same claim as mechanical motion.**

---

## Fault case: two position sensors disagree

Suppose one calibrated position sensor says the carriage reached the target, while another says it did not.

A weak system simply chooses the preferred channel.

A strong verifier asks:

- Were both sensors within calibration validity?
- Did they measure the same physical reference?
- Were their clocks aligned?
- Did either sensor clip, drop samples, or lose power?
- What uncertainty applies?
- Do velocity, force, terminal-switch, or other observations corroborate either interpretation?

If the conflict cannot be resolved strongly enough, the correct outcome can be:

`INCONCLUSIVE`

That is not indecision.

It is a correct statement about evidentiary sufficiency.

---

## Fault case: perfect motion under invalid authority

This is one of the most important experiments in the entire course.

Imagine the current waveform is perfect.

Force is nominal.

Trajectory is nominal.

Final position is nominal.

Vibration and thermal consequences are nominal.

But the authority object is invalid, expired, mismatched, or absent.

The physics passes.

The event acceptance fails.

This proves that Evidence Architecture does not confuse successful consequence with legitimate authority.

The machine did what the command requested.

The evidence cannot establish that it was entitled to do so.

---

## Fault case: evidence is modified after capture

Suppose a valid nominal experiment is completed and packaged.

Later, one retained position value is changed.

The physical event has not changed. It happened in the past.

The issue is now evidence integrity.

If the package uses cryptographic hashes or signatures correctly, the modified content should no longer validate against the original integrity record.

The verifier should reject or quarantine the altered evidence before trusting its physical interpretation.

This gives us another proposition:

**A physically plausible record is not trustworthy when its retained integrity cannot be established.**

---

## Cryptographic consistency and physical consistency are different tests

A valid signature can tell us that a retained record matches what was signed.

It cannot guarantee that the signed values make physical sense.

Imagine a perfectly signed package claiming:

- zero actuator current;
- no stored mechanical or magnetic energy source;
- a large sustained electromagnetic force;
- normal actuator motion.

The signature may verify perfectly.

The physical interpretation still requires investigation.

This is why the final verifier needs more than integrity checking.

It also needs physical consistency checks appropriate to the claim.

---

## Uncertainty-aware acceptance

Suppose the terminal acceptance limit is eight point zero millimeters plus or minus a narrow tolerance.

The measured position lies just inside the limit, but the measurement uncertainty is large enough to cross the boundary.

Can the verifier confidently return PASS?

Not necessarily.

Acceptance should account for how uncertainty relates to the decision boundary according to a predefined rule.

Depending on the protocol, the correct result may be `INCONCLUSIVE` or `INSUFFICIENT_EVIDENCE` rather than a forced pass or fail.

The important principle is:

**Acceptance confidence cannot be stronger than the evidence that feeds it.**

---

## Recompute rather than trusting summary fields

Suppose an Evidence Object contains the field:

`peak_force = 2.3 N`

An independent verifier should not need to trust that number simply because the field exists.

If the raw force samples, calibration identity, baseline rule, time window, and processing method are retained, the verifier can recompute the result.

The same principle applies to:

- velocity;
- acceleration;
- electrical energy;
- impulse;
- force-map predictions;
- fitted RL time constants;
- thermal time constants;
- vibration metrics;
- spectral ratios;
- final acceptance.

A summary claim is stronger when its derivation can be reproduced independently.

---

## Historical model versions must remain attached to historical events

Suppose the force map improves six months later.

Should every old event silently inherit the new model?

No.

The original event should preserve which map version was used at the time of its original interpretation.

A researcher can later reanalyze the raw evidence with the improved model, but that creates a **new derived analysis** linked to the old event.

It should not rewrite history.

The same rule applies to calibration files, filters, thermal models, vibration processing, policy rules, and verifier software.

Versioning is part of evidentiary meaning.

---

## The Evidence Object is a graph, not just a container

A strong VRX Evidence Object either contains or securely references the information needed to reconstruct the claim.

That can include:

- event identity;
- device identity;
- hardware revision;
- firmware and software commit;
- authority and policy result;
- command identity and timestamp;
- configuration identity;
- calibration identities;
- raw electrical, mechanical, thermal, and vibration observations;
- timing and synchronization metadata;
- initial physical state;
- derived metrics;
- model versions;
- uncertainty statements;
- resulting state;
- acceptance result;
- anomaly classification;
- hashes or signatures;
- verifier version and result.

The goal is not one giant file.

The goal is a verifiable graph of relationships.

Which current trace belongs to which command?

Which calibration applies to which sensor?

Which force map supported which prediction?

Which thermal pre-state belongs to which event?

Which mount configuration produced which vibration response?

Which authority object permitted which action?

Evidence architecture makes those relationships explicit.

---

## Acceptance should be multidimensional

Instead of one vague PASS flag, think of final acceptance as several dimensions.

**Authority validity:** Was the action permitted under the required identity, policy, time, and scope?

**Electrical validity:** Did the expected physical electrical event occur?

**Mechanical validity:** Did the expected force and motion occur?

**Resulting-state validity:** Did the system end inside the declared physical acceptance region?

**Evidence integrity:** Do the integrity relationships validate?

**Evidence sufficiency:** Were sampling, calibration, timing, uncertainty, and model support adequate for the requested conclusion?

A final ACCEPT should require every dimension declared mandatory by the protocol.

This prevents one successful subsystem from hiding a failure somewhere else in the chain.

---

## Why `INCONCLUSIVE` is essential

Many engineered systems want binary answers.

Pass or fail.

Yes or no.

Evidence systems need at least one more state.

`INCONCLUSIVE`

Examples include:

- a required sensor clipped;
- the clock alignment is too uncertain;
- two sensors disagree without enough corroboration;
- the model request is outside the validated domain;
- calibration validity cannot be established;
- measurement uncertainty is too large relative to the acceptance boundary;
- a required raw stream is missing.

An inconclusive result does not say the physical event did not occur.

It says the retained evidence cannot support the requested conclusion strongly enough.

That distinction protects scientific integrity.

---

## Experiment 012: nominal event plus controlled faults

The final demonstration has two parts.

### Part One — Nominal full-chain event

Run one bounded, fully authorized, mechanically captive actuation under an accepted configuration.

Capture enough evidence for an independent verifier to reconstruct:

1. what authority existed;
2. what command was issued;
3. whether the actuator branch energized;
4. what current history occurred;
5. what mechanical interaction occurred;
6. what trajectory occurred;
7. what stopping, vibration, and thermal consequences were observed;
8. what resulting state remained;
9. whether the evidence retained integrity;
10. whether the declared acceptance rule passed.

### Part Two — Controlled fault cases

Run approved low-energy fault cases one at a time.

The objective is not simply to make the system fail.

The objective is for the verifier to reject the event for the **correct evidentiary reason**.

---

## A fault is valuable only if it is interpretable

Suppose one test simultaneously disconnects the actuator, changes the position calibration, and invalidates the authority record.

The event will fail, but the result teaches little about the verifier's ability to isolate causes.

Controlled fault injection changes one intended link at a time as much as practical.

When testing invalid authority, keep the physical setup nominal.

When testing a disconnected actuator, keep the position system nominal.

When testing evidence tampering, change the retained evidence after capture rather than altering the physical event.

This preserves causal interpretability.

---

## The twelve-chapter progression

Chapter 1 taught us that an observation is not the same thing as a claim.

Chapter 2 taught us that actuator force is not the same thing as net force.

Chapter 3 taught us that final position is not the same thing as motion history.

Chapter 4 taught us that energy conservation is not the same thing as complete energy observability.

Chapter 5 taught us that the same final state does not imply the same impulse or shock history.

Chapter 6 taught us that commanded electrical state is not the same thing as measured electrical state.

Chapter 7 taught us that current is not a unique description of magnetic force.

Chapter 8 taught us that model prediction is not measurement and that unsupported extrapolation should fail closed.

Chapter 9 taught us that a digital command edge is not an instantaneous current edge.

Chapter 10 taught us that physical pre-state can carry consequence from one event into the next.

Chapter 11 taught us that a source event and its transmitted structural consequence are different physical states.

Chapter 12 brings them together:

**A trustworthy claim requires the right evidence for the right link in the chain.**

---

## The connection back to the physics of evidence

Traditional forensic physics begins with traces left behind after an event and asks what event could have produced them.

VRX adds the complementary direction.

It instruments the event while it happens so that current, force, motion, temperature, vibration, authority, timing, calibration, and resulting state can be preserved as a connected evidence structure.

The principle is the same: physical events leave physical consequences.

The expansion is architectural: we design the system so those consequences remain measurable, attributable, versioned, and independently reviewable.

This is the continuation from the **physics of evidence** to **Evidence Architecture**.

---

## Final listener check

Can valid authority prove that the machine physically acted? No.

Can perfect physical motion prove that the action was authorized? No.

Can a valid signature prove that the recorded physics is plausible? No.

Can physically plausible data be trusted if integrity fails? No.

Should a verifier return a force prediction outside the validated force-map domain? No.

Can `INCONCLUSIVE` be the correct scientific answer? Yes.

What makes a derived result strong evidence? The ability to trace it to raw observations, calibration, timing, processing, model assumptions, uncertainty, and integrity information so another party can reproduce the reasoning.

---

## Closing dialogue

**INSTRUCTOR:** What happened?

**INVESTIGATOR:** We have the observations, calibrated measurements, derived quantities, model predictions, and resulting state.

**INSTRUCTOR:** Was it allowed?

**INVESTIGATOR:** We have the authority and policy evidence.

**INSTRUCTOR:** Can another person verify it?

**INDEPENDENT VERIFIER:** Give me the raw evidence, calibration identities, model versions, timing basis, uncertainty, integrity records, and acceptance rule. I will recompute the conclusion.

**INSTRUCTOR:** Then the course is complete.

The final lesson is not an equation.

It is a discipline:

**Do not ask the actor to be the sole historian of its own behavior.**