# ETS Ranger Research Program

**Status:** R0 concept / research workstream  
**Program:** Lantern Protocol — Evidence Transparency System (ETS)  
**Purpose:** Extend ETS evidence architecture from digital systems into autonomous physical systems.

## Thesis

As autonomous systems increasingly sense, decide, and act in the physical world, recording only the resulting video, telemetry, or action is insufficient. ETS Ranger is a compact unmanned ATV-class research platform intended to demonstrate that the decision process participating in a physical action can be captured, cryptographically bound, preserved, and independently verified.

Ranger is not primarily an ATV product. It is a physical reference implementation of evidence architecture for autonomous machines.

## R0 Mission

Build a van-transportable electrically powered unmanned 4WD ATV-class research platform capable of teleoperation and bounded autonomy, with consequential machine decisions producing cryptographically verifiable ETS evidence records.

### Initial engineering envelope

- Length: 48–60 in
- Width: 30–36 in
- Chassis height: 20–26 in
- Sensor-mast height: 36–48 in
- Target mass: 150–250 lb
- Payload capacity target: 50–100 lb
- Electric 4WD
- 12–16 in off-road pneumatic tires
- 6–9 in ground clearance
- Initial speed envelope: approximately 5–15 mph
- Target mission endurance: 2–6 hours depending on payload
- Cargo-van / pickup transportable
- Zero onboard operators
- Integrated tie-down and ramp/winch loading provisions

These are research targets, not production specifications.

## Architecture

Ranger is organized around three first-class components:

1. **Ranger Core** — mobility, energy, compute, safety, identity, storage, communications, and vehicle telemetry.
2. **Ranger Mission Module** — removable sensor/tool/research payload attached through a controlled payload interface.
3. **ETS Evidence Plane** — captures and binds observations, software/model state, decisions, policy evaluations, commands, physical responses, outcomes, identities, and cryptographic integrity records.

### Design principle

Mechanically ordinary; evidentially extraordinary.

Commodity components should be preferred for R0 where they meet safety and research requirements. Engineering differentiation belongs primarily in evidence capture, machine identity, policy enforcement, modular payload provenance, decision reconstruction, and independent verification.

## Decision evidence pipeline

R0 should evolve toward the following chain:

`Sense → Observe → Decide → Explain → Authorize → Act → Observe Result → Seal → Verify`

A consequential decision event should be capable of binding at least:

- mission identifier
- Ranger device identity
- installed mission-module identity
- operator/controller identity where applicable
- trusted timestamp
- location and vehicle state
- sensor observations and source identities
- relevant software, firmware, model, and configuration versions
- model/algorithm inputs required for reconstruction where policy permits
- candidate actions when available
- selected action
- confidence/quality metadata when applicable
- applicable mission and safety policy constraints
- authorization state
- command issued
- actuator/vehicle response
- observed physical result
- evidence-object hashes
- previous-event linkage
- device signature
- optional witness/verifier attestations

### Bounded identity and epistemic state

Ranger must distinguish observation, authentication, inference, and proof rather than collapsing them into a single identity assertion. Facial recognition against a deliberately small enrolled-principal set can provide efficient local recognition, but a biometric match remains evidence supporting an identity claim rather than absolute proof of the human narrative.

Unknown identity is also evidentiary information. Ranger and ETS should distinguish `NOT_OBSERVED`, `NOT_AVAILABLE`, `UNKNOWN`, `INDETERMINATE`, and `CONTRADICTED` so a verifier can reconstruct not only what Ranger knew at consequence time, but what it did not know and why.

See [Epistemic Identity and Bounded Observability](epistemic-identity.md).

### Cyber-physical observability and consequence custody

Ranger must preserve enough cyber-physical context to distinguish what was observed, what the platform was capable of observing, what decision was made, what command was issued, how the physical system responded, and what result was subsequently observed.

The evidence model is intentionally observation-agnostic: stronger sensors, synchronization, calibration, attestation, and actuator feedback should strengthen the resulting evidence without requiring a new evidence theory.

The cyber-physical research model covers position/pose and coordinate frames, motion/dynamics, relative geometry, clock quality and freshness, environment/terrain, energy/thermal state, mechanical/actuator state, sensor health, compute state, communications, software/model/configuration identity, security/attestation, authority/control mode, policy/mission state, faults/safety state, and physical consequence.

A selected action, issued command, command acknowledgement, actuator response, and observed physical consequence are separate propositions and must not be collapsed.

See [Cyber-Physical Observability Model](cyber-physical-observability.md).

### Executable Ranger Decision Event contract

The first machine-readable research contract is now defined at [`schemas/ranger/decision-event.v0.1.schema.json`](../../../schemas/ranger/decision-event.v0.1.schema.json).

It makes epistemic state explicit in decision evidence and binds claims to source evidence, decision participation, policy, selected action, chain linkage, and optional signature material. A canonical unknown-identity example is maintained at [`examples/decision-event-unknown.json`](examples/decision-event-unknown.json), and architecture tests enforce the stable schema identity and epistemic-state semantics.

The v0.1 contract intentionally treats this as an ETS evidence-object profile rather than a final production wire format. Future revisions should align its canonicalization, signing, Evidence Object identifiers, verifier behavior, and custody rules with the ETS Core contracts.

## Ranger Mission Modules

R0 should use one core chassis rather than separate vehicles. Mission capability is provided through modules.

Potential research modules include:

- **Perception/Scout:** cameras, LiDAR/ranging, GNSS/IMU, environmental sensing.
- **Competition:** safe recreational/scoring payloads for controlled robot-game experiments.
- **Cyber Range:** authorized security-testing equipment for controlled ranges and ETS-on-ETS research.
- **Air/Ground Research:** docking, charging, communications, and evidence handoff for an aerial observation platform.
- **Experimental:** controlled interface for future government, industrial, scientific, inspection, emergency-response, or other authorized research payloads.

Higher-consequence payloads are outside R0 and require separate legal, safety, contractual, policy, and engineering review. The evidence architecture should remain payload-agnostic.

## Payload trust model

A mission module is not trusted merely because it is physically connected.

Before mission activation, Ranger should be able to bind:

`Ranger identity + payload identity + firmware/software + configuration + operator + mission policy`

Payload events must then be attributable to the corresponding hardware/software/configuration state.

## R0 budget hypothesis

R0 should be developed incrementally rather than purchased as a complete autonomous vehicle.

- Early drivetrain/control experiments: hundreds to low thousands of dollars.
- Basic teleoperated rolling research chassis: target approximately $1,500–$3,000 hardware.
- Useful ETS R0 with compute, positioning, cameras, secure storage, safety controls, and ranging: target approximately $3,000–$6,000 hardware.
- Program planning ceiling before explicit review: $10,000.

All figures are planning hypotheses requiring vendor/BOM research before procurement.

## Development gates

Current implementation increment:

- [R0.1 fail-closed mobility safety architecture](safety-architecture.md)
- [R0.1 motion-authority lifecycle evidence](lifecycle-evidence.md)
- [R0.1 deterministic mobility simulation](simulation.md)
- [R0.2 signed local source custody](custody.md)
- [R0.2 clock-qualified cross-boot custody continuity](boot-continuity.md)
- [R0.2 verifier-retained latest-head checkpoints](retained-checkpoints.md)
- [R0.2 custody-key authority history](key-authority.md)
- [Epistemic identity and bounded observability](epistemic-identity.md)
- [Cyber-Physical Observability Model](cyber-physical-observability.md)
- [Ranger Decision Event v0.1 schema](../../../schemas/ranger/decision-event.v0.1.schema.json)
- [Unknown-identity Decision Event example](examples/decision-event-unknown.json)
- [ADR 0001: single fail-closed motion boundary](adr/0001-single-fail-closed-motion-boundary.md)
- [ADR 0002: evidence-shaped mobility simulation](adr/0002-evidence-shaped-mobility-simulation.md)
- [ADR 0003: signed local source custody](adr/0003-signed-local-source-custody.md)
- [ADR 0004: clock-qualified cross-boot custody continuity](adr/0004-clock-qualified-boot-continuity.md)
- [ADR 0005: verifier-retained latest-head checkpoints](adr/0005-verifier-retained-latest-head.md)
- [ADR 0006: authority-relative custody-key history](adr/0006-authority-relative-custody-key-history.md)

### R0.1 — Mobility
- safe rolling chassis
- remote manual control
- hardware emergency stop
- bounded speed
- basic telemetry

### R0.2 — Evidence-aware vehicle
- ETS device identity
- signed vehicle telemetry
- actuator-command evidence
- secure local evidence storage
- mission/session identity

### R0.3 — Perception
- cameras
- GNSS/IMU
- ranging/obstacle sensing
- sensor identity and provenance
- synchronized evidence timeline
- bounded enrolled-principal recognition
- explicit unknown/indeterminate/contradicted identity states
- measurement uncertainty, coordinate-frame, calibration, freshness, and sensor-health evidence where available
- explicit capability/degradation state so inability to observe is not confused with a negative observation

### R0.4 — Bounded autonomy
- waypoint/navigation experiment
- obstacle detection
- constrained action selection
- policy-enforced safety boundaries
- manual takeover / fail-safe behavior

### R0.5 — Decision and consequence reconstruction
- capture decision inputs and relevant machine state
- capture candidate/selected action where available
- capture policy evaluation
- distinguish selected action, issued command, command acknowledgement, actuator response, and observed result
- bind command to actuator/vehicle response and subsequent observations
- preserve known, unknown, unavailable, indeterminate, and contradictory decision context
- preserve relevant capability/degradation state at consequence time
- produce independently verifiable mission evidence package

### R0.6 — Mission-module interface
- physical/electrical/data interface specification
- module identity and attestation
- module lifecycle events
- evidence namespace
- module authorization policy

### R0.7 — Ground/air experiment
- optional aerial observation platform integration
- launch/dock lifecycle evidence
- cross-platform identity
- evidence handoff and timeline correlation

## Canonical first demonstration

Ranger receives a destination inside a controlled test area. During movement, an unexpected benign obstacle is introduced. Ranger detects the obstacle, evaluates bounded alternatives under mission policy, chooses an allowed maneuver or stop, executes the command, and observes the resulting state.

The demonstration succeeds only if an independent verifier can establish from the resulting ETS package:

1. what Ranger perceived;
2. which hardware/software/model produced the relevant observations or decisions;
3. what vehicle, capability, and mission state existed at decision time;
4. what alternatives or constraints participated in the decision where observable;
5. which action was selected and authorized;
6. which physical command was issued;
7. whether the actuator/controller accepted or rejected the command;
8. what the vehicle physically did;
9. what result was subsequently observed;
10. what relevant facts were unknown/unavailable/indeterminate/contradicted and why; and
11. whether the evidentiary chain has been altered.

## Success criterion

> Demonstrate independently verifiable provenance for an autonomous physical decision from sensor observation through physical action and resulting state, while preserving the capability and epistemic limits of the observing system.

## Immediate research backlog

1. Survey compact 4WD electric UGV/chassis candidates against the R0 envelope.
2. Produce R0 BOM with budget / preferred / rugged alternatives.
3. Define Ranger Core electrical and logical architecture.
4. Define the Ranger Payload Bus and trust boundary.
5. Evolve the Ranger Decision Event v0.1 research schema into an ETS Core-aligned cyber-physical evidence-object profile with canonical signing, capability state, measurement quality, consequence custody, and verifier semantics.
6. Map Ranger events into existing ETS Edge, Gateway, Verifier, AI Witness, and Black Box capabilities.
7. Define safety architecture: E-stop, remote takeover, watchdog, geofence, speed limits, fault state, loss-of-comms behavior.
8. Define R0 controlled test course and acceptance criteria.
9. Establish evidence-package verification tests before autonomy implementation, including decision-to-command-to-result reconstruction.
10. Document threat model including sensor spoofing, payload substitution, compromised compute, evidence deletion/tampering, clock/location manipulation, calibration manipulation, stale evidence, sensor/data loss, operator-command repudiation, biometric spoofing, identity-claim poisoning, and false corroboration.
11. Evaluate funding and government research pathways after the non-weaponized R0 architecture is demonstrated.
12. Maintain patent/IP notes around autonomous decision provenance, payload attestation, evidence binding, cross-platform custody, independently verifiable physical-action reconstruction, bounded claims, epistemic absence, capability-state preservation, and consequence custody.

## Research rule

Ranger development should preserve a clean separation between the general-purpose evidence architecture and any future specialized payload. R0 is a non-weaponized research platform. Security testing is restricted to systems/ranges for which explicit authorization exists.
