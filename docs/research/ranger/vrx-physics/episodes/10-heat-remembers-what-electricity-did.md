# VRX Physics Laboratory

## Episode 10 — Heat Remembers What Electricity Did

### ElevenLabs conversational script

**INSTRUCTOR:** We have spent the last several episodes following VRX from command to current, current to magnetic state, magnetic state to force, force to motion, and motion to consequence. Today we are going to study something slower.

**INVESTIGATOR:** Temperature.

**INSTRUCTOR:** Exactly. And temperature changes the way we should think about evidence because thermal state can outlive the electrical event that caused it.

A current pulse may last tens or hundreds of milliseconds. A temperature change can persist for minutes.

That means the system can carry physical memory of prior operation.

---

## 1. Thermal state is part of physical state

Suppose VRX receives the same command twice.

In the first trial, the coil begins near ambient temperature.

In the second, the coil begins already warm after several earlier actuations.

Should we expect the two electrical histories to be identical?

Not necessarily.

Resistance may differ. Current may differ. Magnetic behavior may differ. Force may differ. The resulting temperature rise may differ.

So:

\[
\boxed{Same\ command\not\Rightarrow Same\ consequence\ when\ thermal\ pre-state\ differs}
\]

This is not a software issue. It is physics.

---

## 2. Heat versus temperature

Heat is energy transferred because of a temperature difference or converted from another form of energy.

Temperature describes thermal state.

They are related, but they are not the same quantity.

A large object and a small object can have the same temperature while containing very different amounts of thermal energy.

For an idealized lumped body with approximately constant specific heat:

\[
Q=mc\Delta T
\]

where:

- `Q` is thermal energy change;
- `m` is mass;
- `c` is specific heat capacity;
- `Delta T` is temperature change.

This equation is useful, but VRX is not one perfectly uniform lump. The coil, plunger, frame, air, enclosure, mounting plate, and wiring can all have different temperatures.

---

## 3. Where heating comes from

For a resistive element:

\[
P_R=I^2R
\]

During normal coil operation, resistive heating is an important energy pathway.

But recall Episode 6 and Episode 9: instantaneous electrical input power is:

\[
P_{elec}=VI
\]

During an inductive transient, `VI` and `I^2R` need not be identical because energy can temporarily be stored in the magnetic field.

Over a longer event, part of the electrical input becomes thermal energy.

---

## 4. Temperature changes resistance

For many conductive materials over a limited temperature range, resistance may be approximated by:

\[
R(T)=R_0[1+\alpha(T-T_0)]
\]

where `alpha` is a temperature coefficient.

For VRX, this relation should be treated as a local approximation unless the specific conductor and range are independently established.

The experimental point is simpler:

> Measure whether resistance changes as the actuator warms.

Do not assume the coefficient first and use it to manufacture a temperature claim.

---

## 5. The feedback loop

Thermal and electrical state can interact.

A simplified chain is:

`current -> resistive heating -> temperature rise -> resistance change -> changed current response`

The loop means that thermal pre-state can influence later electrical behavior.

This is why temperature belongs in the provenance of an actuator characterization.

---

## 6. A lumped thermal model

A useful first-order model is:

\[
C_{th}\frac{dT}{dt}=P_{in}(t)-\frac{T-T_{amb}}{R_{th}}
\]

where:

- `C_th` is effective thermal capacitance;
- `R_th` is effective thermal resistance to ambient;
- `T_amb` is ambient temperature.

For simple cooling after input power is removed, an approximate solution is:

\[
T(t)-T_{amb}=(T_0-T_{amb})e^{-t/\tau_{th}}
\]

with:

\[
\tau_{th}=R_{th}C_{th}
\]

This is an approximation, not a statement that the entire actuator has one temperature or one exact thermal time constant.

---

## 7. Why heating and cooling may not match one perfect exponential

Real systems can show multiple thermal time scales.

Examples:

- the winding heats quickly;
- the core heats more slowly;
- the chassis warms later;
- enclosure air changes more slowly still.

If a single exponential does not fit well, preserve that result.

Do not force a one-time-constant model simply because the equation is convenient.

---

## 8. Duty cycle

Duty cycle describes how long a system is energized relative to a repeating period.

For a simple pulse train:

\[
D=\frac{t_{on}}{t_{period}}
\]

A 100 ms pulse every second has a nominal duty cycle of 10 percent.

But duty cycle alone does not fully describe heating.

Two pulse patterns with the same duty cycle may have different peak current, pulse spacing, thermal recovery, or starting temperature.

So:

\[
\boxed{Same\ duty\ cycle\not\Rightarrow Same\ thermal\ history}
\]

---

## 9. Thermal history matters

Consider two schedules with the same average duty cycle.

Schedule A spaces pulses evenly.

Schedule B clusters several pulses together and then waits.

The average on-time may match, but local peak temperature can differ.

Evidence should preserve the actual event sequence, not only the summarized duty cycle.

---

## 10. Temperature sensors do not measure all temperatures

If a temperature sensor is attached to the outside of the actuator housing, it measures temperature near that sensor location.

It does not directly measure winding temperature unless a validated thermal relationship establishes that inference.

This creates an Evidence Architecture distinction:

\[
\boxed{Sensor\ temperature\neq Unobserved\ internal\ temperature}
\]

A thermal model may estimate internal temperature, but that estimate must remain labeled as a model-derived quantity.

---

## 11. Sensor lag

Temperature sensors often respond more slowly than electrical events.

A thermistor, RTD, digital sensor, or thermocouple mounted to a housing has its own thermal mass and contact resistance.

Therefore the recorded peak can be delayed and attenuated relative to the local surface temperature.

Sensor response time is part of measurement provenance.

---

## 12. Contact quality matters

A poorly attached surface probe can report a different temperature than a well-bonded probe.

Relevant context includes:

- sensor type;
- mounting method;
- contact material;
- sensor location;
- calibration;
- sampling interval;
- enclosure airflow.

A thermal trace without sensor-placement provenance is weaker evidence.

---

## 13. Ambient conditions matter

Cooling depends on the environment.

Relevant variables can include:

- ambient temperature;
- airflow;
- enclosure state;
- mounting surface;
- orientation;
- nearby heat sources.

A thermal time constant measured on an open bench should not automatically be treated as valid after VRX is installed inside Ranger.

---

## 14. Thermal pre-state as evidence context

Suppose a force test produces less force than expected.

If the actuator began hot, the explanation may include changed resistance and changed current history.

If the evidence package omitted pre-test temperature, an important explanatory variable is missing.

Therefore the thermal state immediately before an event belongs in the event context.

---

## 15. Residual thermal evidence

Temperature can remain elevated after electrical current returns to zero.

That means physical consequence can persist after action completion.

But be careful:

\[
\boxed{Residual\ temperature\ rise\neq Unique\ proof\ of\ a\ particular\ prior\ action}
\]

Many causes can heat an object.

Temperature is corroborating evidence, not necessarily unique attribution.

---

## 16. Experiment 010 — Heat Remembers

The experiment will use bounded normal VRX-R0 operation.

We will record:

- pre-test actuator temperature;
- ambient temperature;
- voltage and current histories;
- pulse timing;
- position where relevant;
- surface temperature history;
- post-actuation cooling history;
- resistance measurements or estimates under documented conditions.

We will not seek maximum temperature.

The goal is characterization, not thermal-limit discovery.

---

## 17. First comparison: cold versus warm pre-state

Define two bounded starting-state categories using measured temperature windows.

For example conceptually:

- `COLD_BASELINE`: close to stabilized ambient;
- `WARM_BASELINE`: elevated but still well within the approved operating envelope.

Do not invent thresholds from convenience. Establish them from hardware limits and the experimental protocol.

Apply the same nominal command under both conditions and compare:

- current trace;
- resistance context;
- resulting force or motion if included;
- temperature rise.

---

## 18. What would constitute evidence of thermal coupling?

If warmer pre-state consistently changes the current waveform under otherwise controlled conditions, thermal coupling is supported.

If resistance also increases consistently, the causal explanation becomes stronger.

If force changes in a direction consistent with the changed electrical history, the chain gains another corroborating layer.

But each link should remain separately evidenced.

---

## 19. Heating curve

During repeated bounded actuation, plot:

\[
T(t)
\]

Also retain:

\[
I(t),\quad V(t)
\]

and cumulative electrical-energy input:

\[
E_{elec}(t)=\int_0^t V(\tau)I(\tau)d\tau
\]

This lets us compare temperature evolution against actual electrical input rather than command count alone.

---

## 20. Cooling curve

After the final pulse, continue recording temperature while the system cools naturally under controlled conditions.

A normalized temperature difference can be defined as:

\[
\theta(t)=T(t)-T_{amb}
\]

For a first-order model:

\[
\theta(t)=\theta_0e^{-t/\tau_{th}}
\]

Fit the model only if the data support it.

---

## 21. Model classification

Each heating/cooling record should receive an explicit classification such as:

- `FIRST_ORDER_THERMAL_SUPPORTED`
- `FIRST_ORDER_THERMAL_APPROXIMATE`
- `MULTI_TIME_CONSTANT_BEHAVIOR`
- `AMBIENT_NOT_STABLE`
- `SENSOR_PLACEMENT_UNCERTAIN`
- `INSUFFICIENT_COOLING_WINDOW`
- `TEMPERATURE_SENSOR_CLIPPED`
- `OUTSIDE_VALIDATED_THERMAL_DOMAIN`

Unsupported records should not receive a falsely precise thermal time constant.

---

## 22. Estimated thermal time constant

Where supported, estimate:

\[
\tau_{th}
\]

from the cooling trace.

Retain:

- fit interval;
- fitting method;
- residuals;
- uncertainty;
- ambient definition;
- sensor identity;
- model version.

`tau_th` is a model-derived parameter, not a direct sensor observation.

---

## 23. Resistance-temperature coupling

Where the experimental method supports resistance estimation, compare:

\[
R\;versus\;T
\]

A simple local regression may be useful.

Do not assume linearity outside the observed region.

If a local coefficient is estimated, its valid temperature range must travel with the coefficient.

---

## 24. Thermal acceptance is not one number

A maximum allowed temperature may be part of safety acceptance, but thermal validity can require more context:

- starting temperature;
- maximum temperature;
- dwell duration;
- cooling state;
- sensor location;
- uncertainty;
- hardware rating.

A reading below a limit does not prove every internal component is below that limit unless that inference is independently validated.

---

## 25. Evidence Architecture connection

A thermal event chain can be represented as:

`authority -> command -> electrical input -> resistive/magnetic energy pathways -> temperature evolution -> residual thermal state -> later electrical/mechanical consequence`

This is consequence custody across time.

The state produced by one event can become the pre-state of the next event.

---

## 26. State lineage

For sequential VRX events, record something like:

`event_n resulting thermal state -> event_n+1 initial thermal state`

That relationship is important.

It prevents each action from being analyzed as though the hardware magically returned to ambient between commands.

---

## 27. A useful ETS proposition

The same command can be valid, authorized, and correctly executed in software while producing a different physical result because physical pre-state changed.

Therefore:

\[
\boxed{Command\ equivalence\neq Physical\ state\ equivalence}
\]

and:

\[
\boxed{Physical\ pre-state\ is\ part\ of\ consequence\ context}
\]

---

## 28. Independent verifier dialogue

**INDEPENDENT VERIFIER:** You say Trial B produced less current than Trial A even though the command was identical. Why?

**INVESTIGATOR:** Trial B began at a higher measured actuator temperature. The measured resistance context was also higher, and the current waveform differed.

**INDEPENDENT VERIFIER:** Are you claiming temperature uniquely caused the difference?

**INVESTIGATOR:** Not from temperature alone. We preserve the electrical waveform, resistance context, ambient conditions, sensor calibration, and other controlled variables. The thermal explanation is supported by the combined evidence.

**INDEPENDENT VERIFIER:** Good. And the surface temperature is not automatically winding temperature?

**INVESTIGATOR:** Correct. Any internal-temperature estimate remains model-derived unless directly instrumented or separately validated.

---

## 29. Prediction challenge

1. If initial coil resistance is higher and supply behavior is otherwise comparable, what may happen to steady current? It may decrease.
2. Does equal duty cycle guarantee equal peak temperature? No.
3. Does a hot housing uniquely prove a specific command occurred? No.
4. Does a command ending mean its physical consequences have ended? Not necessarily.
5. Can the resulting state of one event affect the next event? Yes.

---

## 30. Research artifact

Experiment 010 should eventually produce a thermal characterization package containing:

- device identity;
- sensor identities and locations;
- ambient context;
- raw temperature traces;
- voltage/current histories;
- pulse schedule;
- resistance context;
- heating/cooling model fits;
- residuals;
- model classification;
- validated temperature domain;
- uncertainty statement;
- provenance hash/version.

A future artifact name might resemble:

`VRX-R0-THERM-0001`

The name matters less than the discipline: the artifact must expose what was observed, what was inferred, and where the inference is valid.

---

## 31. Final lesson

Heat is not merely a loss term at the end of an energy equation.

Thermal state changes electrical behavior, can alter later mechanical consequence, persists after commands complete, and carries evidence about system history.

But temperature must be interpreted carefully. A sensor measures its local environment, not every internal component. A residual temperature rise corroborates prior energy deposition but does not uniquely identify its source. A thermal time constant is model-derived. Equal commands need not produce equal consequences when initial state differs.

### Evidence Architecture summary

\[
\boxed{Same\ command\not\Rightarrow Same\ consequence\ when\ thermal\ pre-state\ differs}
\]

\[
\boxed{Sensor\ temperature\neq Unobserved\ internal\ temperature}
\]

\[
\boxed{Residual\ temperature\ rise\neq Unique\ proof\ of\ prior\ action}
\]

\[
\boxed{Physical\ pre-state\ is\ part\ of\ consequence\ context}
\]

### Assignment

Complete Experiment 010 in `../experiments/010-heat-remembers.md`.

Review textbook sections on thermal energy, heat capacity, conduction, convection, Newton-style cooling models, resistive heating, and temperature dependence of resistance.

### Next episode

**Episode 11 — Why Machines Shake**

The next lesson studies oscillation, damping, natural frequency, resonance, transmissibility, structural excitation, and how an actuator event can propagate through the Ranger chassis and contaminate other sensors.