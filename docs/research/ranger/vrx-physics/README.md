# VRX-R0 Physics Laboratory Curriculum

**System:** ETS VectorRail (VRX)  
**Scope:** Low-voltage, enclosed, captive electromagnetic linear-actuator research platform  
**Status:** Twelve-module documentation and spoken-book curriculum complete; experimental execution/review remains  
**Purpose:** Teach the physics needed to model, measure, and verify VRX-R0 behavior while connecting every lesson to ETS Evidence Architecture.

## Safety boundary

This curriculum is for the captive VRX-R0 laboratory configuration only. Nothing in this curriculum requires or assumes free-launching projectiles. All motion remains mechanically captive, enclosed, bounded, and within manufacturer-rated operating limits.

The curriculum does not require suppression defeat, deliberate high-voltage spike generation, destructive impacts, maximum-force searches, or thermal-limit searches.

## Learning objective

The curriculum follows two parallel chains:

**Physics:**

`Voltage/current -> magnetic state -> force -> acceleration -> velocity -> position -> stopping/impulse -> vibration/thermal consequence`

**Evidence:**

`Authority -> command -> actuation -> observation -> physical consequence -> resulting state -> Evidence Object -> independent verification`

The student should be able to separate prediction, observation, calibrated measurement, derived quantity, model inference, acceptance decision, and independently verifiable evidence.

## Research episodes and spoken-book edition

The curriculum now has two complementary presentation layers.

### Research/engineering episodes

`episodes/` preserves the denser technical lectures, equations, experiment references, and phase-review context used during development and laboratory design.

### ElevenReader book edition

`book/` is the narration-safe edition. It contains conventional front matter and twelve chapters rewritten so the mathematics is **explained conversationally before and after the equation** rather than depending on a listener to decode symbolic notation by ear.

The book preface explicitly connects the traditional **physics of evidence**—using physical laws to reconstruct events from traces—to Evidence Architecture, where instrumented systems preserve observations, calibration, authority, physical consequences, provenance, and integrity while events occur.

Use `book/README.md` as the production manifest and `book/front-matter.md` + `book/chapters/01...12` as the ElevenReader manuscript source.

`book/technical-review.md` records the full twelve-module physics/mathematics review and the corrections incorporated into the spoken edition.

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
   - voltage, current, resistance, power, energy, resistive dissipation, temperature-dependent resistance, measurement boundaries

7. **Episode 7 — Turning Current Into Force**
   - magnetic field, flux, permeability, air gaps, ferromagnetic behavior, saturation, hysteresis, co-energy, position-dependent force

8. **Episode 8 — Build the VRX Force Map**
   - empirical `F(I,x)` surface, repeated grid observations, interpolation, validated domain, uncertainty, residuals, holdout validation, fail-closed out-of-domain handling

9. **Episode 9 — Why Current Doesn't Change Instantly**
   - flux linkage, inductance, RL current rise, moving-inductance term, time constant, current-onset latency, stored magnetic energy, protected turn-off behavior

### Phase 3 — Thermal, vibration, and evidence closure

10. **Episode 10 — Heat Remembers What Electricity Did**
    - temperature vs heat transfer
    - internal-energy generation
    - heating/cooling curves and thermal time constants
    - duty-cycle and pulse-history effects
    - resistance-temperature coupling
    - sensor placement/lag
    - thermal pre-state and state lineage

11. **Episode 11 — Why Machines Shake**
    - mass-spring-damper model
    - undamped natural frequency and damping
    - resonance and ring-down
    - source-event normalization
    - three-axis acceleration and coordinate frames
    - empirical spectral acceleration ratio vs frequency-response estimation
    - FFT/PSD/cross-spectral/coherence processing provenance
    - aliasing, clipping, bandwidth, and timing limits
    - rigid vs compliant vs isolated/floating mounting
    - Ranger sensor/compute mounting implications
    - structural path as consequence provenance

12. **Episode 12 — Can We Prove What Happened?**
    - full-chain consequence custody
    - authority vs physical consequence
    - uncertainty-aware acceptance
    - controlled low-energy fault injection
    - evidence integrity vs physical plausibility
    - `INCONCLUSIVE` / `INSUFFICIENT_EVIDENCE`
    - independent recomputation
    - Evidence Object / evidence graph closure

## Repository layout

```text
docs/research/ranger/vrx-physics/
├── README.md
├── lecture-plan.md
├── lab-notebook.md
├── book/
│   ├── README.md
│   ├── front-matter.md
│   ├── technical-review.md
│   └── chapters/
│       ├── 01-how-do-we-know-anything-happened.md
│       ├── 02-why-does-vrx-move.md
│       ├── 03-motion-has-a-history.md
│       ├── 04-where-did-the-energy-go.md
│       ├── 05-the-physics-of-stopping.md
│       ├── 06-electricity-before-magnetism.md
│       ├── 07-turning-current-into-force.md
│       ├── 08-build-the-vrx-force-map.md
│       ├── 09-why-current-doesnt-change-instantly.md
│       ├── 10-heat-remembers-what-electricity-did.md
│       ├── 11-why-machines-shake.md
│       └── 12-can-we-prove-what-happened.md
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
│   ├── 10-heat-remembers-what-electricity-did.md
│   ├── 11-why-machines-shake.md
│   └── 12-can-we-prove-what-happened.md
├── experiments/
│   ├── 003-reconstruct-the-motion.md
│   ├── 004-follow-the-energy.md
│   ├── 005-the-physics-of-shock.md
│   ├── 006-electricity-before-magnetism.md
│   ├── 007-current-becomes-force.md
│   ├── 008-build-the-vrx-force-map.md
│   ├── 009-inductance-and-current-rise.md
│   ├── 010-heat-remembers.md
│   ├── 011-vibration-and-transmissibility.md
│   └── 012-full-chain-consequence-custody.md
└── phases/
    ├── 02-kinematics-review.md
    ├── 03-energy-accounting-review.md
    ├── 04-impulse-shock-review.md
    ├── 05-electricity-review.md
    ├── 06-magnetism-force-review.md
    ├── 07-force-map-review.md
    ├── 08-inductance-transients-review.md
    ├── 09-thermal-state-review.md
    ├── 10-vibration-transmissibility-review.md
    └── 11-evidence-closure-review.md
```

## Review workflow

For every module:

1. Review conceptual physics.
2. Check equations, sign conventions, assumptions, and model domain.
3. Review the experiment for safety and measurability.
4. Confirm raw observations are distinct from calibrated/derived/model values.
5. Confirm Evidence Architecture claims do not exceed captured evidence.
6. Confirm important formulas are explained verbally in the book edition.
7. Preserve uncertainty, sampling, calibration, and model provenance.
8. Merge only after the phase is technically accepted.

## Technical-review highlights incorporated into the book

The full review corrected or clarified several important points:

- interval overlap is not used as a standalone statistical significance test;
- `F = ma` is net external force, not automatically actuator force;
- energy ledgers use declared boundaries and avoid double-counting energy categories;
- impulse analysis preserves direction, rebound, sampling/bandwidth limits, and possible parallel force paths;
- electrical formulas are applied at the correct element/boundary and operating condition;
- electromechanical force uses magnetic co-energy and an explicit coordinate/sign convention;
- force-map interpolation, uncertainty, and extrapolation are distinct;
- the inductive voltage relation uses `v = Ri + dλ/dt` and includes motion-dependent flux-linkage change where applicable;
- thermal language distinguishes internal-energy generation from heat transfer;
- vibration analysis distinguishes an event-specific spectral magnitude ratio from a true frequency-response estimate;
- logarithmic-decrement and coherence interpretations are bounded correctly;
- evidence closure separates authority, consequence, integrity, physical plausibility, and sufficiency.

## Related VRX artifacts

This curriculum complements the existing VRX laboratory acceptance, Evidence Object, verifier, external-validation, and consequence-custody documentation already in `docs/research/ranger/` and `validation/releases/vectorrail-vrx/`.

## Documentation status

- [x] Curriculum architecture
- [x] Lab notebook architecture
- [x] Episodes 1–12
- [x] Experiments 003–012 protocols
- [x] Phase reviews through evidence closure
- [x] Full twelve-module technical physics/mathematics review
- [x] Conventional book front matter
- [x] Spoken-math / ElevenReader rewrite for Chapters 1–12
- [x] Physics-of-evidence → Evidence Architecture preface
- [x] ElevenReader production manifest
- [ ] Experimental data templates
- [ ] VRX-R0 hardware commissioning record
- [ ] Execute experiments and populate datasets
- [ ] Independent replication/review package
- [ ] Final narration QA and publication export

## Current review gate

**Phase 11 — Full-Chain Evidence Closure and Book Technical Review**

Review:

- `episodes/12-can-we-prove-what-happened.md`
- `experiments/012-full-chain-consequence-custody.md`
- `phases/11-evidence-closure-review.md`
- `book/technical-review.md`
- `book/front-matter.md`
- `book/chapters/01...12`

The final course proposition is:

> **A trustworthy claim requires the right evidence for the right link in the chain.**

After this gate is accepted, the curriculum is complete at the documentation/protocol level. The next work is experimental execution, independent review, narration QA, and publication packaging.