# Captive Electromagnetic Actuation Evidence Demonstrator

**Status:** Research design / non-weaponized laboratory demonstrator  
**Program:** ETS Ranger / Cyber-Physical Evidence Architecture  
**Purpose:** Demonstrate independently verifiable provenance across an electrical command, electromagnetic actuation, measurable motion, thermal response, and resulting physical state.

## Scope and safety boundary

This experiment is intentionally **not a projectile launcher**. It uses a short-travel, mechanically captive armature inside an enclosed test channel. The research objective is instrumentation, evidence capture, causal reconstruction, and comparison of commanded versus observed physical state—not velocity, range, penetration, or delivered impact energy.

The design shall remain low-energy and current-limited, with no free-flight projectile, no explosive or chemical propellant, no energetic payload, and no optimization for weapon performance. Mechanical stops and containment must prevent the moving element from leaving the apparatus under any single credible fault.

## Research thesis

A conventional controller log can establish that software issued an actuation command. It cannot, by itself, establish that electrical energy was delivered, electromagnetic actuation occurred, the armature moved, or the expected resulting physical state was reached.

The demonstrator creates a compact evidence chain:

`Operator authority → control command → pre-actuation electrical state → switching event → measured electrical response → armature motion → thermal response → resulting state → ETS seal → independent verification`

The experiment therefore provides a controlled analogue for Ranger mobility, industrial actuators, robotic systems, AI-controlled infrastructure, and other cyber-physical systems in which intent, command, response, and consequence are distinct propositions.

## Principles demonstrated

The apparatus should make the following phenomena measurable without requiring a free projectile:

- electromagnetic/Lorentz-force actuation;
- relationship between electrical current and mechanical response;
- resistive heating and thermal accumulation;
- contact resistance and repeatability;
- electrical-to-mechanical/thermal energy conversion;
- command/actuation timing;
- sensor synchronization and uncertainty;
- mechanical travel and final-state verification;
- controller claim versus independently observed consequence;
- fault, blocked-motion, and degraded-sensor evidence.

Useful governing relationships for analysis include:

`Q = I² R t`

for resistive heating, and the simplified rail-actuator relationship

`F ≈ 1/2 L' I²`

where the latter is treated as a model to compare with observation, not as an assertion that measured motion proves the model perfectly.

## Mechanical design

### Test channel

- Short, enclosed linear actuation channel.
- Two conductive rails arranged for electromagnetic actuation research.
- Captive conductive armature that cannot exit the channel.
- Hard mechanical end stops independent of software control.
- Secondary retention/containment around the armature path.
- Transparent or instrumented enclosure may be used only where its material and geometry remain appropriate for the experiment's low-energy containment requirement.
- No provision for interchangeable free-flight projectiles.

### Armature

The armature should be selected for reliable low-energy electrical contact and repeatable short travel. Its mass, dimensions, material identity, and measured starting position become evidence metadata. The design should favor repeatability and sensor visibility over acceleration.

### Travel

Travel should be deliberately short and bounded. Position sensing must cover the complete allowed motion envelope, including both mechanical stops. The apparatus should remain informative even when movement is only millimeters to centimeters.

## Electrical architecture

The electrical subsystem shall prioritize bounded energy and observability.

Required characteristics:

- isolated low-voltage research supply or other appropriately bounded laboratory source;
- explicit current limiting;
- hardware master disconnect;
- normally-safe switching state;
- pre-actuation voltage measurement;
- current measurement during the actuation event;
- post-event discharge/safe-state verification where stored-energy components are used;
- fused or otherwise protected fault path appropriate to the laboratory source;
- no software-only safety dependency.

Exact source voltage, capacitance, pulse-current ceiling, conductor dimensions, and switching-device sizing are intentionally left as laboratory engineering parameters to be established through formal electrical safety review and bench characterization. The acceptance criterion is measurable captive motion at the lowest practical energy, not maximum acceleration.

## Instrumentation

### Required channels

| Channel | Purpose | Evidence role |
|---|---|---|
| Command state | Records requested actuation | Intent |
| Authorization state | Establishes whether command was permitted | Authority |
| Supply voltage | Establishes electrical state before/during event | Capability/energy evidence |
| Actuation current | Observes delivered electrical event | Physical response |
| Rail/contact temperature | Observes thermal consequence | Resulting state |
| Armature position | Observes displacement and final position | Physical consequence |
| Enclosure/interlock state | Establishes safety boundary state | Policy/capability |
| Controller clock | Correlates command and local telemetry | Timeline |
| Independent sensor clock where available | Tests timing independence | Corroboration |
| Fault state | Records protection/interlock activation | Safety consequence |

### Optional channels

- high-rate voltage measurement across the actuator;
- magnetic-field sensing suitable for qualitative/relative observation;
- accelerometer on the captive carriage;
- independent optical position sensing;
- ambient temperature;
- rail temperature at multiple locations;
- contact-resistance characterization between runs;
- camera observation synchronized to the event timeline.

Each sensor should carry identity, calibration/characterization metadata, sample rate, clock source, uncertainty/quality metadata where known, and capability/degradation state.

## ETS evidence model

Each actuation trial should produce a trial-scoped evidence package containing at least:

- experiment/trial identifier;
- apparatus identity;
- controller identity;
- operator identity or authorized principal reference;
- software/firmware/configuration versions;
- armature identity and physical configuration;
- sensor identities and calibration/characterization references;
- interlock and containment state;
- authorization decision;
- requested command;
- pre-event electrical and thermal state;
- switching-event timestamp;
- sampled voltage/current observations;
- motion observations;
- thermal observations;
- fault/protection events;
- final position and safe-state observations;
- relevant measurement uncertainty and clock quality;
- hashes/source ancestry for raw measurement artifacts;
- chain linkage to prior event where applicable;
- device signature/seal;
- optional independent witness/verifier receipt.

ETS must preserve the distinction among:

`selected/requested action ≠ issued command ≠ switching event ≠ electrical response ≠ mechanical response ≠ observed resulting state`

No downstream state may be inferred solely because an upstream log entry exists.

## Canonical test matrix

### T1 — Baseline actuation

An authorized low-energy actuation produces measurable current, captive displacement, and a measurable resulting state. ETS reconstructs the complete chain.

### T2 — Command with mechanically blocked response

The system records an authorized command and electrical response while the captive element is deliberately prevented from normal movement using a safe test fixture. The evidence package must distinguish command execution from absent/limited mechanical consequence.

### T3 — Command rejected by interlock

An unsafe or intentionally open interlock causes the actuation request to fail closed. ETS records requested action, policy/interlock state, rejection, and absence of downstream electrical/mechanical consequence.

### T4 — Sensor degradation

One non-safety measurement channel is intentionally unavailable or marked degraded. ETS must represent the missing observation as `NOT_AVAILABLE`, `UNKNOWN`, or another appropriate epistemic state rather than manufacturing a negative measurement.

### T5 — Independent-observation disagreement

Two benign position/temperature observations disagree beyond the declared tolerance. ETS preserves both source observations, their independence/ancestry, quality metadata, and a `CONTRADICTED` or `INDETERMINATE` derived state where appropriate.

### T6 — Repeated-run thermal accumulation

Multiple low-energy trials are performed within the approved thermal envelope. The evidence package demonstrates that identical commands need not imply identical initial conditions or consequences, because rail/contact temperature and resistance can evolve between trials.

## Acceptance criteria

The demonstrator succeeds when an independent verifier can determine, without trusting the controller's narrative alone:

1. who/what was authorized to request the event;
2. what command was requested and issued;
3. whether safety/interlock policy permitted actuation;
4. what electrical state existed before the event;
5. whether a measurable electrical event occurred;
6. whether the captive armature moved;
7. what thermal response was observed;
8. what final mechanical and electrical safe state was observed;
9. which observations were unavailable, degraded, contradictory, or dependent on a common source;
10. whether the evidence chain has been modified since sealing.

Successful reconstruction does **not** prove that every sensor was correct or that the simplified electromagnetic model is objectively true. It proves what the identified instrumentation reported, under the documented configuration and observability limits.

## Materials/BOM categories

This is a research BOM specification rather than a procurement recipe. Candidate parts should be selected only after the electrical/mechanical safety envelope is fixed.

### Mechanical

- rigid nonconductive/appropriately insulated base structure;
- two conductive experimental rails;
- captive conductive armature/carriage;
- mechanical guides;
- independent hard stops;
- secondary retention/containment enclosure;
- guarded terminals and cable strain relief;
- fixture for safe blocked-motion test.

### Electrical/control

- bounded laboratory DC energy source;
- hardware current limiting/protection;
- master disconnect;
- appropriately rated switching element;
- hardware interlock chain;
- low-voltage controller/data-acquisition computer;
- isolated or appropriately protected measurement interfaces;
- emergency/manual safe-state control.

### Sensors

- current sensor;
- voltage measurement channel;
- at least one position/displacement sensor;
- rail/contact temperature sensors;
- enclosure/interlock sensor;
- optional independent optical position sensor;
- optional magnetic-field sensor;
- optional accelerometer;
- optional synchronized camera.

### ETS integration

- ETS Edge-compatible evidence collector;
- local append-only evidence storage;
- device identity/signing capability;
- trusted/qualified timestamp source where available;
- Gateway/Verifier interface for post-trial verification;
- optional AI Witness analysis of the resulting evidence package, clearly separated from primary measurement evidence.

## Safety requirements

- Armature remains captive for every test.
- Enclosure remains closed/interlocked during energization.
- Mechanical retention does not depend on software.
- Current/energy limits do not depend solely on application software.
- Hardware disconnect is accessible before each test.
- Energization is fail-closed on interlock or controller fault.
- Thermal limits are defined before repeated-run testing.
- A trial cannot begin when required safety telemetry is unavailable.
- Stored energy, if any, has an observable safe/discharged state before handling.
- No explosive, chemical propellant, energetic payload, free projectile, penetration target, or velocity/range optimization is part of this research workstream.

## Relationship to Ranger

The demonstrator is intentionally simpler than Ranger while preserving the same evidence problem:

`Observation/State → Decision/Authority → Command → Physical actuator response → Consequence → Resulting-state observation`

Lessons from this apparatus should feed Ranger's actuator-command evidence, consequence custody, sensor independence, capability/degradation semantics, clock qualification, and physical-state reconstruction requirements.

The demonstrator can therefore serve as a benchtop precursor to higher-complexity Ranger experiments and as an accessible teaching example for Evidence Architecture.

## Next engineering artifacts

1. Define a machine-readable `electromagnetic-actuation-trial` research evidence profile aligned with the Ranger Decision Event and ETS Core Evidence Object contracts.
2. Define telemetry units, sample-time semantics, uncertainty fields, sensor identity, and source-ancestry requirements.
3. Create synthetic baseline, blocked-response, rejected-command, degraded-sensor, and contradictory-observation evidence fixtures.
4. Add verifier tests proving that command success cannot be inferred from controller logs alone.
5. Define a laboratory safety/acceptance checklist before any physical implementation.
6. Map the experiment into the Evidence Architecture lecture/manual as a compact cyber-physical consequence-custody case study.
