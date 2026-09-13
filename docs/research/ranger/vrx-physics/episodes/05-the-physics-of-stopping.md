# VRX Physics Laboratory

## Episode 5 — The Physics of Stopping

### ElevenLabs conversational script

**INSTRUCTOR:** In the last episode we followed energy through VRX. We asked where electrical input went and learned that an incomplete measurement ledger is not the same thing as violated conservation of energy.

Today we are going to study a much shorter event.

The carriage is moving.

Then it stops.

The entire event may last only milliseconds.

And yet that brief interval can determine the largest mechanical load seen by the carriage, the terminal structure, the VRX chassis, and eventually Ranger.

Our question is:

> If two trials begin with essentially the same moving carriage and end with the carriage stopped, can the mechanical consequence be very different?

**INVESTIGATOR:** Yes. If one stop is more compliant, it can spread the stopping event over more time.

**INSTRUCTOR:** Exactly. But we are going to make that statement carefully, because stopping time, peak force, impulse, rebound, deformation, damping, and sensor bandwidth are related but they are not interchangeable.

---

## 1. Momentum

Linear momentum is:

\[
p=mv
\]

where:

- `p` is momentum;
- `m` is mass;
- `v` is velocity.

Momentum is a vector. Direction matters.

If the positive direction is toward the terminal stop and a 0.25 kg carriage approaches at 0.20 m/s:

\[
p=(0.25)(0.20)=0.050\,kg\cdot m/s
\]

If it comes to rest:

\[
p_f=0
\]

Then the carriage momentum change is:

\[
\Delta p=p_f-p_i=-0.050\,kg\cdot m/s
\]

The negative sign tells us that the impulse on the carriage acts opposite the approach direction.

---

## 2. Impulse

Impulse is the time integral of force:

\[
J=\int_{t_1}^{t_2}F(t)\,dt
\]

The impulse-momentum theorem gives:

\[
J=\Delta p
\]

This is one of the most useful relationships in the VRX laboratory because we can estimate the same physical event in two different ways.

One route uses a force-time history.

The other uses mass and before/after velocity.

If the two estimates disagree beyond their uncertainty, we have something to investigate.

---

## 3. Average force is not peak force

For a defined contact interval:

\[
F_{avg}=\frac{J}{\Delta t}=\frac{\Delta p}{\Delta t}
\]

Suppose the carriage undergoes the same momentum change in two hypothetical trials.

Trial A stops it in 5 milliseconds.

Trial B stops it in 20 milliseconds.

For the same `Δp`, Trial B has one quarter of the average force magnitude.

But that does **not** automatically tell us the peak force.

Peak force depends on the shape of the force-time curve.

Two pulses may have equal area and very different peaks.

That is why we preserve the waveform rather than only a single summary number.

---

## 4. Area under the force-time curve

Picture a graph with force on the vertical axis and time on the horizontal axis.

The area under that curve is impulse.

A narrow, tall pulse and a broader, shorter pulse can have similar areas.

That is the first intuition behind compliant stopping.

A more compliant terminal condition can increase the duration of the interaction and often reduce the peak force for otherwise comparable conditions.

But we must test that empirically.

Real systems contain damping, elasticity, friction, structural vibration, sensor dynamics, and sometimes rebound.

---

## 5. Rebound changes the momentum calculation

**INSTRUCTOR:** Suppose the carriage approaches the stop at positive 0.20 meters per second and finishes at rest. What is the velocity change?

**INVESTIGATOR:** Negative 0.20 meters per second.

**INSTRUCTOR:** Correct.

Now suppose it approaches at positive 0.20 meters per second, compresses the terminal element, and rebounds at negative 0.05 meters per second.

The velocity change is:

\[
\Delta v=-0.05-(+0.20)=-0.25\,m/s
\]

The magnitude of the momentum change is now larger than in the no-rebound case.

Therefore we cannot say:

> Same incoming momentum means same impulse.

The correct statement is:

> Impulse equals the **actual change in momentum**, which depends on both the incoming and outgoing velocity.

This matters directly to our rigid-versus-compliant comparison.

---

## 6. Stopping distance

Time is not the only way a terminal element can spread a stop.

A compliant element may also increase stopping distance.

Work-energy gives us another view:

\[
W=\Delta K
\]

If a stopping force acts over a longer distance, the same change in kinetic energy can be distributed over that distance differently.

In an idealized constant-force model:

\[
F\Delta x=\Delta K
\]

so a larger stopping distance can correspond to a smaller average force magnitude for the same energy change.

Again, real force is generally not constant.

The experiment must measure the actual force and motion histories.

---

## 7. Momentum and energy answer different questions

Momentum and kinetic energy are related but not interchangeable.

Momentum:

\[
p=mv
\]

Kinetic energy:

\[
K=\frac12mv^2
\]

Velocity appears linearly in momentum and quadratically in kinetic energy.

Therefore two systems can have the same momentum but different kinetic energies, or the same kinetic energy but different momenta.

This is why Episode 4 and Episode 5 are separate.

Energy accounting tells us about transformations.

Impulse tells us about the force-time interaction required to change momentum.

---

## 8. A numerical example

Suppose:

\[
m=0.25\,kg
\]

and the carriage reaches:

\[
v_i=0.20\,m/s
\]

before contact.

If it stops without rebound:

\[
\Delta p=0-(0.25)(0.20)=-0.050\,kg\cdot m/s
\]

The impulse magnitude is:

\[
|J|=0.050\,N\cdot s
\]

If the interaction lasts 10 ms:

\[
\Delta t=0.010\,s
\]

then the average force magnitude is:

\[
F_{avg}=\frac{0.050}{0.010}=5.0\,N
\]

If the same momentum change occurred over 25 ms:

\[
F_{avg}=\frac{0.050}{0.025}=2.0\,N
\]

The example illustrates the relationship. It is not a design target for VRX.

Our hardware measurements and component ratings determine the real experimental envelope.

---

## 9. What is shock?

In engineering, shock is a transient mechanical disturbance involving comparatively rapid changes in force, acceleration, velocity, or stress.

The exact definition depends on the discipline and measurement context.

For VRX we care about the short-duration mechanical response produced when moving mass is decelerated and that disturbance propagates into the surrounding structure.

We are not trying to produce damaging shock.

We are trying to measure a low-energy, bounded transient well enough to understand:

- force-time behavior;
- acceleration response;
- transmission into supporting structure;
- terminal compliance;
- rebound;
- settling.

---

## 10. Source event versus transmitted event

Imagine a load cell near the carriage terminal interface and an accelerometer on the VRX chassis.

The load cell observes part of the source interaction.

The chassis accelerometer observes part of the transmitted structural response.

Those are not the same measurement.

A terminal event can contain frequencies or local forces that do not appear identically at the chassis sensor.

Structure, joints, damping, mass distribution, and sensor mounting all affect transmission.

Later, Episode 11 will treat vibration and transmissibility formally.

For now we establish the source transient and its immediate consequence.

---

## 11. Force-time history

Suppose Stop A produces a waveform with a sharp peak and short duration.

Stop B produces a lower peak and broader duration.

If both bring the carriage to essentially the same final velocity and begin from comparable approach velocity, their impulse estimates should be broadly consistent after uncertainty is considered.

But if Stop B causes significant rebound, its momentum change can differ.

Therefore the experiment must record both:

\[
v_{before}
\]

and:

\[
v_{after}
\]

rather than assuming `v_after=0`.

---

## 12. Peak force can be misleading by itself

**INSTRUCTOR:** Which stop is better, the one with the smaller peak force?

**INVESTIGATOR:** Probably the smaller peak.

**INSTRUCTOR:** Maybe. But what else should we inspect?

A smaller peak might accompany:

- a longer pulse;
- greater displacement;
- more rebound;
- longer settling time;
- different vibration transmission;
- a second impact;
- sensor clipping or bandwidth limitation.

A single peak number cannot fully characterize the event.

This is another example of the Evidence Architecture principle we developed in Episode 3:

> A summary state is not a complete event history.

---

## 13. Sampling rate matters

Stopping events are fast.

If the force sensor produces a narrow pulse but we sample too slowly, we may miss the true peak or distort the pulse shape.

This is temporal under-sampling.

A sensor can be accurate in steady-state conditions and still be unsuitable for transient measurement because its bandwidth is inadequate.

So for every force or acceleration channel we need to know more than the nominal sensor range.

We care about:

- sampling frequency;
- sensor bandwidth;
- amplifier bandwidth;
- filter settings;
- timestamp resolution;
- synchronization;
- clipping limits.

---

## 14. Aliasing

If a signal changes faster than the sampling system can represent, higher-frequency content can masquerade as lower-frequency behavior.

That phenomenon is aliasing.

We will explore it more deeply in the vibration episode.

For this experiment the practical lesson is simple:

> Do not claim a force or acceleration transient is fully characterized unless the measurement chain has sufficient temporal response for the event being studied.

That limitation belongs in the evidence record.

---

## 15. Sensor clipping

Suppose a load cell channel reaches its maximum measurable value and remains there for several samples.

The displayed peak may look clean.

But the real peak might have exceeded the instrument range.

The correct interpretation is not:

`PEAK_FORCE = sensor maximum`

It is closer to:

`PEAK_FORCE >= measurable limit; exact peak not observed`

That distinction prevents false precision.

---

## 16. Time synchronization

Our momentum estimate may use position-derived velocity.

Our impulse estimate may use force samples.

To compare them, the time windows must refer to the same physical event.

Clock offsets can make correct sensors appear inconsistent.

So we preserve:

- raw timestamps;
- synchronization method;
- clock source;
- estimated timing uncertainty;
- processing windows.

Once again, provenance is part of the physics result.

---

## 17. Defining contact

When exactly does the stopping event begin?

Possibilities include:

- first force above a predefined noise threshold;
- first terminal-position threshold crossing;
- a combined condition;
- a model-based contact estimate.

There is no universal answer for every apparatus.

The important requirement is that the definition be specified before comparing trials and retained with the analysis.

Changing the contact-window rule after seeing the data can change calculated impulse.

---

## 18. Integrating force numerically

Real force data is sampled.

Instead of evaluating an analytical integral exactly, we approximate:

\[
J=\int F(t)dt
\]

from discrete samples.

One common method is the trapezoidal rule:

\[
J\approx\sum_i \frac{F_i+F_{i+1}}{2}(t_{i+1}-t_i)
\]

The calculation should record:

- raw force samples;
- raw timestamps;
- baseline correction method;
- contact-window definition;
- numerical integration method;
- software version.

Then an independent verifier can recompute the impulse.

---

## 19. Momentum-based impulse estimate

A second estimate is:

\[
J_p=m(v_{after}-v_{before})
\]

This estimate depends on:

- carriage mass;
- velocity measurement;
- timing;
- definition of before/after windows;
- uncertainty in derived velocity.

The force-integrated impulse and momentum-change impulse should not be expected to match to infinite precision.

They should be compared with uncertainty and model limitations explicitly considered.

---

## 20. Physical-consistency check

Now we gain another cross-domain consistency test.

Force history predicts impulse:

\[
J_F=\int Fdt
\]

Motion history predicts momentum change:

\[
J_p=\Delta p
\]

If:

\[
J_F\not\approx J_p
\]

beyond the justified uncertainty, possible explanations include:

- force calibration error;
- position/velocity estimation error;
- timing mismatch;
- missing force path;
- sensor bandwidth limitations;
- unmodeled contact;
- incorrect mass;
- data-processing error.

We investigate rather than automatically choosing one sensor as truth.

---

## 21. Multiple force paths

A subtle point: the load cell may not measure every mechanical force acting on the carriage.

If part of the force is transmitted through another structural path, the measured interface impulse may differ from total carriage momentum change.

This is not necessarily a violation of mechanics.

It may mean the measurement boundary does not contain every force path.

That idea parallels Episode 4's energy boundary.

Instrumentation defines what part of the system we can directly observe.

---

## 22. The experiment

Experiment 005 compares two low-energy, mechanically captive terminal conditions.

Condition A is the baseline, relatively stiff terminal configuration.

Condition B is a documented compliant terminal configuration.

Both remain mechanically retained inside the enclosure and within all component ratings.

We are not trying to maximize force or shock.

We are trying to compare transient response under matched, low-energy approach conditions.

---

## 23. What must be matched?

For a defensible comparison, keep or match as closely as practical:

- carriage mass;
- starting configuration;
- approach direction;
- approach velocity window;
- actuator state before contact;
- temperature;
- sensor configuration;
- sampling settings;
- software/firmware;
- structural mounting.

The terminal condition is the independent variable.

---

## 24. What do we measure?

At minimum, preserve enough information to estimate:

- `v_before`;
- `v_after`;
- force versus time;
- contact duration;
- peak observed force;
- impulse;
- maximum terminal displacement if instrumented;
- rebound behavior;
- settling time.

Where available, also record chassis acceleration to begin connecting source impulse to transmitted disturbance.

---

## 25. Pre-experiment prediction

Before seeing data, write a prediction.

For example:

> Under matched low-energy approach conditions, I predict the compliant terminal condition will increase interaction duration and reduce peak observed force relative to the stiffer condition. I will not assume equal impulse unless measured before/after velocities support comparable momentum change.

That last sentence matters.

It prevents us from forcing the experiment to match a simplified classroom narrative.

---

## 26. Data table

A useful summary table is:

| Trial | Terminal | Mass | v_before | v_after | Contact duration | Peak force | Force-integral impulse | Momentum-change impulse | Rebound | Settling |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|

But preserve the full waveforms too.

The table is derived evidence.

The waveforms are the observations from which much of that table is calculated.

---

## 27. Comparing peak force

After repeated trials, compare the peak-force distributions rather than only one trial.

Ask:

- Is the reduction repeatable?
- Are there outliers?
- Is either sensor near saturation?
- Did approach velocities actually match?
- Did one stop rebound more?
- Did temperature or alignment drift?

A single visually impressive waveform is not a characterization.

---

## 28. Comparing impulse

For each trial, calculate:

\[
J_F=\int Fdt
\]

and:

\[
J_p=m(v_{after}-v_{before})
\]

Then compare the two.

Do not hide disagreement.

The disagreement can reveal measurement-boundary problems that would otherwise remain invisible.

---

## 29. Same final state, different consequence

Imagine both conditions eventually leave the carriage stationary at the same final location.

A final-state-only record might conclude:

`PASS: carriage stopped at terminal location`

But one trial may have experienced:

- a much higher force peak;
- shorter contact duration;
- greater chassis acceleration;
- additional bounce;
- longer ringing.

Therefore:

\[
\boxed{Same\ final\ state\not\Rightarrow Same\ mechanical\ consequence}
\]

This proposition is central to consequence custody.

---

## 30. Ranger connection

Ranger will eventually contain components with very different mechanical sensitivities:

- cameras;
- IMUs;
- compute modules;
- storage;
- connectors;
- batteries;
- mounted research modules.

A structure surviving a transient is not the only concern.

We also care whether the transient contaminates sensor data, disrupts connectors, causes temporary compute faults, shifts calibration, or changes the evidence generated during the event.

That is why mechanical isolation becomes both a reliability problem and an evidence-quality problem.

---

## 31. Isolation is not simply softness

A common intuition is:

> Softer is always better.

That is false.

Too much compliance can increase travel, allow repeated impacts, produce rebound, create low-frequency motion, or interact badly with structural resonance.

Effective isolation is a system-design problem involving mass, stiffness, damping, forcing frequency, geometry, and allowable displacement.

Episode 11 will model this with:

\[
m\ddot{x}+c\dot{x}+kx=F(t)
\]

For now, Experiment 005 gives us measured source data that can later drive that analysis.

---

## 32. Evidence Architecture connection

The event can now be represented as:

`approach state -> contact -> force-time history -> momentum change -> terminal response -> transmitted disturbance -> resulting state`

A strong evidence record distinguishes:

- initial state;
- raw time-series observations;
- calibration;
- event-window definition;
- derived impulse;
- derived momentum change;
- peak-force claim;
- rebound claim;
- acceptance result;
- uncertainty.

The verifier should be able to recompute the derived quantities from retained observations.

---

## 33. Independent verifier dialogue

**INDEPENDENT VERIFIER:** You say the compliant stop reduced shock.

**INVESTIGATOR:** More precisely, under matched low-energy approach conditions it produced a lower observed force peak and a longer contact interval.

**INDEPENDENT VERIFIER:** Did impulse remain the same?

**INVESTIGATOR:** We did not assume that. We measured before/after velocity, integrated the force waveform, and compared both impulse estimates.

**INDEPENDENT VERIFIER:** Was there rebound?

**INVESTIGATOR:** It was measured and included in `v_after`.

**INDEPENDENT VERIFIER:** Could the sensor have missed the actual peak?

**INVESTIGATOR:** The evidence package includes sensor bandwidth, sample rate, range, filter settings, and clipping status so that limitation can be evaluated.

**INSTRUCTOR:** That is the level of precision we want.

---

## 34. Physics consistency versus evidence validity

A force-time waveform can be cryptographically authentic and still be physically incomplete.

A momentum calculation can be mathematically correct and still depend on a biased velocity estimate.

A final-state observation can be correct and still omit a damaging transient.

So we preserve multiple layers:

1. authenticity and integrity;
2. measurement provenance;
3. calibration and uncertainty;
4. physical consistency;
5. semantic interpretation;
6. acceptance policy.

None substitutes for the others.

---

## 35. Prediction challenge

Pause after each question.

**Question 1:** If the momentum change is fixed and stopping time increases, what happens to average force magnitude?

**Answer:** It decreases.

**Question 2:** Does that prove peak force decreases by exactly the same ratio?

**Answer:** No. Peak force depends on waveform shape.

**Question 3:** If the carriage rebounds, can the impulse magnitude exceed the value required merely to bring it to rest?

**Answer:** Yes.

**Question 4:** If two trials end at the same position, did they necessarily experience the same force history?

**Answer:** No.

**Question 5:** If the force-integrated impulse differs from the momentum-change estimate, which one is automatically wrong?

**Answer:** Neither. Investigate calibration, timing, force paths, bandwidth, processing, and uncertainty.

---

## 36. Lab assignment

Complete Experiment 005 — The Physics of Shock.

Before testing, define:

- the terminal conditions;
- the approach-velocity matching rule;
- contact-window rule;
- force and motion sampling configuration;
- clipping criteria;
- uncertainty sources;
- predicted differences.

Perform repeated low-energy captive trials.

Preserve raw time series before calculating summary metrics.

Then compare:

- contact duration;
- observed peak force;
- `J_F`;
- `J_p`;
- rebound;
- settling;
- any measured chassis response.

---

## 37. Textbook study before Episode 6

Review sections covering:

- linear momentum;
- impulse;
- collisions;
- force-time graphs;
- work-energy comparison;
- conservation of momentum;
- elastic and inelastic collision concepts.

Pay special attention to the system boundary used in momentum-conservation problems.

A carriage by itself does not conserve momentum while an external stop acts on it.

A larger closed system must include the structures exchanging momentum.

---

## 38. Final lesson

The physics of stopping teaches us something broader than how to protect hardware.

A final state can look completely normal while the path to that state contains a severe transient.

Therefore evidence of state is not automatically evidence of consequence history.

For VRX:

\[
\boxed{J=\int Fdt=\Delta p}
\]

provides a bridge between force evidence and motion evidence.

And the larger Evidence Architecture lesson is:

\[
\boxed{Same\ result\not\Rightarrow Same\ consequence}
\]

In Episode 6 we cross from mechanics into electricity and ask a different foundational question:

> What exactly do voltage, current, resistance, and electrical power tell us about the physical state of the actuator before magnetism enters the picture?
