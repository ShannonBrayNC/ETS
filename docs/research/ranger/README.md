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

### R0.4 — Bounded autonomy
- waypoint/navigation experiment
- obstacle detection
- constrained action selection
- policy-enforced safety boundaries
- manual takeover / fail-safe behavior

### R0.5 — Decision reconstruction
- capture decision inputs and relevant machine state
- capture candidate/selected action where available
- capture policy evaluation
- bind command to observed result
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
3. what vehicle and mission state existed at decision time;
4. what alternatives or constraints participated in the decision where observable;
5. which action was selected and authorized;
6. which physical command was issued;
7. what the vehicle actually did;
8. what result was subsequently observed; and
9. whether the evidentiary chain has been altered.

## Success criterion

> Demonstrate independently verifiable provenance for an autonomous physical decision from sensor observation through physical action and resulting state.

## Immediate research backlog

1. Survey compact 4WD electric UGV/chassis candidates against the R0 envelope.
2. Produce R0 BOM with budget / preferred / rugged alternatives.
3. Define Ranger Core electrical and logical architecture.
4. Define the Ranger Payload Bus and trust boundary.
5. Define the Ranger Decision Event schema as an ETS evidence-object profile.
6. Map Ranger events into existing ETS Edge, Gateway, Verifier, AI Witness, and Black Box capabilities.
7. Define safety architecture: E-stop, remote takeover, watchdog, geofence, speed limits, fault state, loss-of-comms behavior.
8. Define R0 controlled test course and acceptance criteria.
9. Establish evidence-package verification tests before autonomy implementation.
10. Document threat model including sensor spoofing, payload substitution, compromised compute, evidence deletion/tampering, clock/location manipulation, and operator-command repudiation.
11. Evaluate funding and government research pathways after the non-weaponized R0 architecture is demonstrated.
12. Maintain patent/IP notes around autonomous decision provenance, payload attestation, evidence binding, cross-platform custody, and independently verifiable physical-action reconstruction.

## Research rule

Ranger development should preserve a clean separation between the general-purpose evidence architecture and any future specialized payload. R0 is a non-weaponized research platform. Security testing is restricted to systems/ranges for which explicit authorization exists.
