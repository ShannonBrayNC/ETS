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
   - measurement
   - accuracy vs precision
   - uncertainty
   - calibration
   - repeatability/reproducibility
   - raw observation vs inference

2. **Episode 2 — Why Does VRX Move?**
   - Newton's laws
   - free-body diagrams
   - force balance
   - mass and inertia
   - friction and breakaway force
   - direct vs indirect force measurement

3. **Episode 3 — Motion Has a History**
   - position, velocity, acceleration
   - trajectory reconstruction
   - sampling and derivatives
   - overshoot and abnormal paths
   - resulting state vs event history

4. **Episode 4 — Where Did the Energy Go?**
   - work
   - power
   - kinetic energy
   - system boundaries
   - energy accounting
   - efficiency
   - residuals and physical consistency

5. **Episode 5 — The Physics of Stopping**
   - momentum
   - impulse
   - force-time curves
   - average vs peak force
   - rebound and momentum change
   - compliant vs stiff stopping
   - transient sensor bandwidth and clipping
   - shock transfer
   - force-impulse vs momentum-change consistency

### Phase 2 — Electricity and electromagnetism

6. **Episode 6 — Electricity Before Magnetism**
   - voltage as a measured potential difference
   - current as measured branch flow
   - resistance and appropriate use of Ohm's law
   - electrical power and energy
   - Joule heating
   - measurement boundaries
   - cold vs warm electrical state
   - resistance-versus-temperature characterization
   - commanded vs observed electrical state

7. **Episode 7 — Turning Current Into Force**
   - magnetic field and magnetic flux
   - permeability and magnetic-circuit intuition
   - air-gap effects
   - ferromagnetic behavior
   - saturation and hysteresis
   - position-dependent force
   - measured current vs modeled magnetic state
   - interface force observation
   - model residuals and provenance

8. **Episode 8 — Build the VRX Force Map**
   - empirical `F(I,x)` characterization
   - repeated grid observations
   - interpolation versus direct observation
   - explicit measured domain
   - local-support rules
   - repeatability and uncertainty
   - residual and holdout validation
   - thermal/history context
   - immutable versioned force-map artifacts
   - strict out-of-domain handling

9. **Episode 9 — Why Current Doesn't Change Instantly**
   - inductance and flux linkage
   - Faraday/Lenz intuition
   - series-RL current rise
   - electrical time constant
   - current-onset latency
   - position- and temperature-dependent effective inductance
   - residual/model-fit analysis
   - stored magnetic energy as a model-derived quantity
   - protected turn-off/flyback behavior
   - transient sampling, bandwidth, and timing provenance

### Phase 3 — thermal, vibration, and evidence closure

10. **Episode 10 — Heat Remembers What Electricity Did**
    - thermal energy
    - heat capacity
    - equilibrium
    - thermal time constants

11. **Episode 11 — Why Machines Shake**
    - springs
    - damping
    - natural frequency
    - resonance
    - transmissibility
    - Ranger mounting implications

12. **Episode 12 — Can We Prove What Happened?**
    - experimental design
    - model validation
    - fault injection
    - consequence custody
    - independent verification

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
│   └── 09-why-current-doesnt-change-instantly.md
├── experiments/
│   ├── 003-reconstruct-the-motion.md
│   ├── 004-follow-the-energy.md
│   ├── 005-the-physics-of-shock.md
│   ├── 006-electricity-before-magnetism.md
│   ├── 007-current-becomes-force.md
│   ├── 008-build-the-vrx-force-map.md
│   └── 009-inductance-and-current-rise.md
└── phases/
    ├── 02-kinematics-review.md
    ├── 03-energy-accounting-review.md
    ├── 04-impulse-shock-review.md
    ├── 05-electricity-review.md
    ├── 06-magnetism-force-review.md
    ├── 07-force-map-review.md
    └── 08-inductance-transients-review.md
```

Later episodes should continue one lecture/experiment pair at a time so each physics layer and its evidence claims can be reviewed before the next is added.

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
- [ ] Episode 10
- [ ] Episode 11
- [ ] Episode 12
- [ ] ElevenLabs production pass
- [ ] Experimental data templates
- [ ] VRX-R0 hardware commissioning record
- [ ] Independent-review package

## Current review gate

**Phase 8 — Inductance, RL Transients, and Magnetic-Energy Evidence**

Review `episodes/09-why-current-doesnt-change-instantly.md`, `experiments/009-inductance-and-current-rise.md`, and `phases/08-inductance-transients-review.md` before proceeding to thermal-state characterization.

The central transient-evidence propositions are:

\[
\boxed{Command\ edge\neq Current\ edge}
\]

\[
\boxed{Same\ pulse\ width\not\Rightarrow Same\ current\ history}
\]

\[
\boxed{Inductance\ estimate\neq Direct\ inductance\ observation}
\]

and:

\[
\boxed{Calculated\ magnetic\ energy\neq Direct\ energy\ observation}
\]

The primary experiment characterizes the normal, protected current-rise waveform. Installed inductive suppression remains in place; the curriculum does not require open-circuit spike tests or deliberate generation of high-voltage flyback events.

Where a local first-order series-RL model is supported, the evidence package may estimate:

\[
\tau=\frac{L}{R}
\]

and:

\[
L_{est}=\tau R
\]

but only with retained waveform data, temperature/resistance context, fit provenance, residuals, uncertainty, and explicit model-support classification.