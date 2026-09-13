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

4. **Episode 4 — Where Did the Energy Go?**
   - work
   - power
   - kinetic energy
   - energy accounting
   - efficiency

5. **Episode 5 — The Physics of Stopping**
   - momentum
   - impulse
   - force-time curves
   - compliant vs rigid stopping
   - shock transfer

### Phase 2 — Electricity and electromagnetism

6. **Episode 6 — Electricity Before Magnetism**
   - voltage
   - current
   - resistance
   - power
   - Joule heating

7. **Episode 7 — Turning Current Into Force**
   - magnetic fields
   - flux
   - permeability
   - ferromagnetic behavior
   - electromagnetic force

8. **Episode 8 — Build the VRX Force Map**
   - empirical `F(I,x)` characterization
   - air-gap dependence
   - nonlinearity
   - saturation

9. **Episode 9 — Why Current Doesn't Change Instantly**
   - inductance
   - RL transients
   - time constants
   - stored magnetic energy
   - flyback physics

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
└── episodes/
    ├── 01-how-do-we-know-anything-happened.md
    └── 02-why-does-vrx-move.md
```

Future phases should add Episodes 03–12 one at a time so each can be reviewed before the next is drafted.

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

This curriculum is intended to complement the existing VRX laboratory acceptance, Evidence Object, verifier, external-validation, and consequence-custody documentation already in `docs/research/ranger/` and `validation/releases/vectorrail-vrx/`.

## Phase status

- [x] Curriculum architecture
- [x] Lab notebook architecture
- [x] Episode 1 draft
- [x] Episode 2 draft
- [ ] Episode 3
- [ ] Episode 4
- [ ] Episode 5
- [ ] Episode 6
- [ ] Episode 7
- [ ] Episode 8
- [ ] Episode 9
- [ ] Episode 10
- [ ] Episode 11
- [ ] Episode 12
- [ ] ElevenLabs production pass
- [ ] Experimental data templates
- [ ] VRX-R0 hardware commissioning record
- [ ] Independent-review package
