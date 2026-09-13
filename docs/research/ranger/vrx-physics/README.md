# VRX-R0 Physics Laboratory Curriculum

**System:** ETS VectorRail (VRX)  
**Scope:** Low-voltage, enclosed, captive electromagnetic linear-actuator research platform  
**Status:** Phased curriculum under review  
**Purpose:** Teach the physics needed to model, measure, and verify VRX-R0 behavior while connecting every lesson to ETS Evidence Architecture.

## Safety boundary

This curriculum is for the captive VRX-R0 laboratory configuration only. Nothing in this curriculum requires or assumes free-launching projectiles. All motion remains mechanically captive, enclosed, bounded, and within manufacturer-rated operating limits.

## Learning objective

The curriculum follows two parallel chains:

**Physics:**

`Voltage/current -> magnetic field -> force -> acceleration -> velocity -> position -> impulse -> vibration/heat`

**Evidence:**

`Authority -> command -> actuation -> observation -> physical consequence -> resulting state -> Evidence Object -> independent verification`

The student should be able to separate prediction, observation, calibrated measurement, derived quantity, inference, acceptance decision, and independently verifiable evidence.

## Course phases

### Phase 1 — Measurement and mechanics

1. **Episode 1 — How Do We Know Anything Happened?**
   - measurement, uncertainty, calibration, repeatability, raw observation vs inference

2. **Episode 2 — Why Does VRX Move?**
   - Newton's laws, free-body diagrams, mass, net force, friction, direct vs indirect force measurement

3. **Episode 3 — Motion Has a History**
   - position, velocity, acceleration, sampling, derivatives, overshoot, event history vs final state

4. **Episode 4 — Where Did the Energy Go?**
   - work, power, kinetic energy, system boundaries, energy accounting, efficiency, residuals

5. **Episode 5 — The Physics of Stopping**
   - momentum, impulse, force-time curves, average vs peak force, rebound, compliant vs stiff stopping, shock transfer

### Phase 2 — Electricity and electromagnetism

6. **Episode 6 — Electricity Before Magnetism**
   - voltage, current, resistance, power, energy, Joule heating, temperature-dependent resistance, measurement boundaries

7. **Episode 7 — Turning Current Into Force**
   - magnetic field, flux, permeability, air gaps, ferromagnetic behavior, saturation, hysteresis, position-dependent force

8. **Episode 8 — Build the VRX Force Map**
   - empirical `F(I,x)` surface, repeated grid observations, interpolation, validated domain, uncertainty, residuals, holdout validation, fail-closed out-of-domain handling

9. **Episode 9 — Why Current Doesn't Change Instantly**
   - inductance, flux linkage, RL current rise, time constant, current-onset latency, effective inductance, stored magnetic energy, protected turn-off behavior

### Phase 3 — Thermal, vibration, and evidence closure

10. **Episode 10 — Heat Remembers What Electricity Did**
    - thermal energy and temperature
    - resistive heating and energy pathways
    - heating/cooling curves
    - effective thermal time constants
    - duty cycle and pulse-history effects
    - resistance-temperature coupling
    - sensor placement and lag
    - thermal pre-state as consequence context
    - state lineage across sequential events

11. **Episode 11 — Why Machines Shake**
    - springs, damping, natural frequency, resonance, transmissibility, structural excitation, Ranger mounting implications

12. **Episode 12 — Can We Prove What Happened?**
    - experimental design, model validation, fault injection, consequence custody, independent verification

## Repository layout

```text
docs/research/ranger/vrx-physics/
├── README.md
├── lecture-plan.md
├── lab-notebook.md
├── episodes/
│   ├── 01-how-do-we-know-anything-happened.md
│   ├── 02-why-does-vrx-move.md
│   ├── 03-motion-has-a-history.md
│   ├── 04-where-did-the-energy-go.md
│   ├── 05-the-physics-of-stopping.md
│   ├── 06-electricity-before-magnetism.md
│   ├── 07-turning-current-into-force.md
│   ├── 08-build-the-vrx-force-map.md
│   ├── 09-why-current-doesnt-change-instantly.md
│   └── 10-heat-remembers-what-electricity-did.md
├── experiments/
│   ├── 003-reconstruct-the-motion.md
│   ├── 004-follow-the-energy.md
│   ├── 005-the-physics-of-shock.md
│   ├── 006-electricity-before-magnetism.md
│   ├── 007-current-becomes-force.md
│   ├── 008-build-the-vrx-force-map.md
│   ├── 009-inductance-and-current-rise.md
│   └── 010-heat-remembers.md
└── phases/
    ├── 02-kinematics-review.md
    ├── 03-energy-accounting-review.md
    ├── 04-impulse-shock-review.md
    ├── 05-electricity-review.md
    ├── 06-magnetism-force-review.md
    ├── 07-force-map-review.md
    ├── 08-inductance-transients-review.md
    └── 09-thermal-state-review.md
```

## Review workflow

For every episode:

1. Review the conceptual physics.
2. Check equations and assumptions.
3. Review the proposed experiment for safety and measurability.
4. Confirm raw observations are distinct from derived values.
5. Confirm Evidence Architecture claims do not exceed the evidence captured.
6. Merge only after the episode is technically accepted.
7. Build the next episode from the accepted baseline.

## Related VRX artifacts

This curriculum complements the existing VRX laboratory acceptance, Evidence Object, verifier, external-validation, and consequence-custody documentation already in `docs/research/ranger/` and `validation/releases/vectorrail-vrx/`.

## Phase status

- [x] Curriculum architecture
- [x] Lab notebook architecture
- [x] Episode 1 draft
- [x] Episode 2 draft
- [x] Episode 3 draft
- [x] Experiment 003 protocol
- [x] Episode 4 draft
- [x] Experiment 004 protocol
- [x] Episode 5 draft
- [x] Experiment 005 protocol
- [x] Episode 6 draft
- [x] Experiment 006 protocol
- [x] Episode 7 draft
- [x] Experiment 007 protocol
- [x] Episode 8 draft
- [x] Experiment 008 protocol
- [x] Episode 9 draft
- [x] Experiment 009 protocol
- [x] Episode 10 draft
- [x] Experiment 010 protocol
- [ ] Episode 11
- [ ] Episode 12
- [ ] ElevenLabs production pass
- [ ] Experimental data templates
- [ ] VRX-R0 hardware commissioning record
- [ ] Independent-review package

## Current review gate

**Phase 9 — Thermal State, Duty Cycle, and Consequence Context**

Review `episodes/10-heat-remembers-what-electricity-did.md`, `experiments/010-heat-remembers.md`, and `phases/09-thermal-state-review.md` before proceeding to vibration and transmissibility characterization.

The central thermal-evidence propositions are:

\[
\boxed{Same\ command\not\Rightarrow Same\ consequence\ when\ thermal\ pre-state\ differs}
\]

\[
\boxed{Same\ duty\ cycle\not\Rightarrow Same\ thermal\ history}
\]

\[
\boxed{Sensor\ temperature\neq Unobserved\ internal\ temperature}
\]

\[
\boxed{Residual\ temperature\ rise\neq Unique\ proof\ of\ prior\ action}
\]

and:

\[
\boxed{Physical\ pre-state\ is\ part\ of\ consequence\ context}
\]

The primary experiment characterizes bounded heating/cooling behavior and cold-versus-warm pre-state effects without approaching thermal limits. Where supported, a first-order cooling model may estimate `tau_th`; unsupported records retain an explicit model classification rather than receiving a forced numeric parameter.
