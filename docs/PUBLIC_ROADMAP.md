# ETS Public Roadmap

**Status:** Public planning document  
**Program:** Lantern Protocol — Evidence Transparency System (ETS)  
**Updated:** September 2026

ETS is being developed as a layered Evidence Architecture platform for independently verifiable digital and cyber-physical evidence. This roadmap shows the direction of the work without representing research items, prototypes, or qualification targets as production-ready features.

The rollout is deliberately gradual. Capabilities move forward only when their evidence, verification, safety, and operational assumptions are explicit enough to support the next stage.

> **Roadmap rule:** research is not release, a passing experiment is not production qualification, and a signed record is not automatically proof that every real-world fact was observed.

## How to read this roadmap

The roadmap is organized by capability maturity rather than promised ship dates.

- **Foundation** — protocol, verifier, core evidence semantics, and reproducible research.
- **Qualification** — deployment hardening, independent verification, failure testing, and operational evidence.
- **Pilot** — bounded use with explicit assumptions and rollback paths.
- **Research** — exploratory work used to test Evidence Architecture in new domains.
- **Future** — dependent on successful completion of earlier gates.

Phases may overlap. A later research track may begin before an earlier product track is commercially available, but no later phase should be treated as a production dependency until its own evidence gates are satisfied.

---

## Phase 0 — ETS Core and independent verification

**Primary objective:** establish a defensible evidence foundation before expanding the product surface.

Current work includes:

- deterministic evidence canonicalization and hashing;
- append-only evidence logs and Merkle proofs;
- Evidence Object semantics and provenance boundaries;
- signed tree-head and verifier workflows;
- durable local persistence experiments;
- tenant/workspace isolation and authentication hardening;
- reproducible research artifacts and formal models;
- explicit distinction between integrity, observation, inference, and truth;
- independent verification tools and certificates.

**Public milestone:** a usable alpha/reference implementation that can produce and independently verify bounded evidence artifacts without claiming production trust-service maturity.

---

## Phase 1 — ETS Edge and ETS Verify

**Primary objective:** capture evidence close to where events occur and make verification portable.

### ETS Edge

Edge is the local evidence-capture and continuity tier. The program is evaluating:

- device identity;
- local signed custody chains;
- intermittent/offline operation;
- bounded synchronization;
- tamper-evident evidence packaging;
- local durability and recovery;
- controlled publication to upstream ETS services.

### ETS Verify / Verifier

Verify is the independent verification surface for checking ETS artifacts without requiring trust in the originating system.

Work includes:

- evidence-object verification;
- inclusion and consistency proof validation;
- signed checkpoint verification;
- certificate/report generation;
- retained-head comparison;
- verifier federation and disagreement research.

**Gate to advance:** an external verifier must be able to reproduce the relevant integrity and provenance checks from exported artifacts.

---

## Phase 2 — ETS Gateway and enterprise connectors

**Primary objective:** connect operational systems to ETS without turning source systems into implicit evidence authorities.

Gateway work includes:

- durable evidence relay;
- identity and authorization boundaries;
- bounded ingestion;
- replay and recovery behavior;
- source-system provenance;
- cloud publication and migration qualification;
- controlled connector execution.

The first major enterprise connector track is Microsoft 365. Research and qualification work covers SharePoint, Microsoft Graph, Purview-related activity, identity, retrieval provenance, and the distinction between discovery metadata and independently retrieved evidence content.

Additional connectors can follow the same model after the Gateway boundary is proven reusable.

**Gate to advance:** source retrieval, evidence creation, custody, and verification must remain distinguishable end to end.

---

## Phase 3 — ETS AI Witness and accountable agents

**Primary objective:** make AI and agent activity inspectable without relying on the AI system to be the sole historian of its own behavior.

Research areas include:

- agent identity and delegated authority;
- policy evaluation evidence;
- model/tool/configuration provenance;
- prompt/input and output commitments where appropriate;
- tool invocation evidence;
- externally observed consequences;
- resulting-state evidence;
- chain-of-custody across agent, tool, target, and verifier;
- alignment with emerging agent-control and Zero Trust architectures.

The central Evidence Architecture distinction is:

**Control governs what an agent may do. Evidence establishes what can later be independently proven about what occurred.**

**Gate to advance:** action records must be correlated with external observations or resulting state when the claimed consequence exists outside the agent itself.

---

## Phase 4 — ETS Vault and ETS Black Box

**Primary objective:** preserve evidence through long retention periods and adverse incidents.

### ETS Vault

Vault is the long-term preservation tier for evidence and associated artifacts under explicit retention and custody policy.

### ETS Black Box

Black Box is the incident-survivability capture tier. Research focuses on preserving bounded evidence windows before, during, and after consequential events.

Areas of work include:

- immutable or retention-governed storage;
- independent publication receipts;
- archive retrieval audits;
- key lifecycle and authority history;
- failure-resilient local capture;
- reconstruction from independently retained checkpoints;
- post-incident verification without assuming the originating machine survived intact.

**Gate to advance:** survivability and retrievability must be demonstrated independently of the primary runtime path.

---

## Phase 5 — ETS Mobile

**Primary objective:** extend Evidence Architecture to mobile devices as first-class evidence sources rather than treating phones only as endpoints.

Research areas include:

- device-bound evidence identity;
- camera, location, motion, and local-sensor provenance;
- offline capture and later synchronization;
- user-authorized evidence creation;
- mobile chain-of-custody;
- cross-device correlation;
- bounded privacy-preserving profiles.

Mobile work is intended to reuse ETS Core, Edge, Gateway, Verify, and custody semantics rather than create a separate evidence theory.

---

## Phase 6 — Ranger R0: cyber-physical Evidence Architecture

**Primary objective:** test whether ETS can preserve independently verifiable provenance across the digital-to-physical boundary.

Ranger is a compact unmanned ground research platform. It is not primarily an ATV product; it is a physical reference implementation for Evidence Architecture.

The terrestrial R0 program is intentionally first.

Planned progression:

1. fail-closed mobility and emergency-stop architecture;
2. deterministic simulation;
3. signed local source custody;
4. perception and synchronized telemetry;
5. bounded autonomy;
6. authority and policy evidence;
7. actuator-command evidence;
8. physical-response observation;
9. resulting-state evidence;
10. independent consequence reconstruction.

The target evidence chain is:

`Observation → Interpretation → Decision → Authority → Policy Evaluation → Command → Actuator Response → Physical Consequence → Resulting State → Evidence Object → Independent Verification`

Ranger will be fully characterized on land before any marine work begins.

**Gate to advance:** an independent verifier must be able to reconstruct a bounded machine decision and physical consequence while preserving uncertainty, sensor limitations, source ancestry, and the distinction between command, response, and observed result.

---

## Phase 7 — VectorRail / VRX controlled actuation research

**Primary objective:** create a repeatable non-weaponized physical disturbance for testing consequence custody, shock/vibration evidence, actuator provenance, and cyber-physical reconstruction.

The current R0 concept is a captive, low-energy electromagnetic/mechanical actuation demonstrator. Its purpose is measurement, not projectile performance.

Research includes:

- command-to-current correlation;
- measured impulse and vibration;
- structural and isolated-frame response;
- timing and sensor synchronization;
- resulting-state observation;
- acceptance evidence;
- Evidence Object packaging;
- independent verification.

Larger variants remain future research and are gated by measured vehicle dynamics, safety limits, structural response, and evidentiary value rather than by actuator scale alone.

---

## Phase 8 — Ranger Marine: surface and submerged evidence research

**Primary objective:** extend Ranger into a domain where motion, navigation, communications, and observation uncertainty become substantially more complex.

Marine Ranger will not begin until terrestrial Ranger is operational and its baseline dynamics and evidence model are understood.

The research sequence is expected to move through:

1. dry marine instrumentation integration;
2. static flotation and trim qualification;
3. shallow tethered testing;
4. powered surface operation;
5. controlled submergence;
6. submerged navigation;
7. surface-relay communications;
8. bounded autonomous underwater operation;
9. repeatable disturbance/consequence experiments.

### Six-degree-of-freedom evidence

Marine operation requires explicit treatment of:

- surge;
- sway;
- heave;
- roll;
- pitch;
- yaw.

The evidence model must preserve both state and uncertainty rather than reducing motion to a single position or heading.

Research will therefore examine:

- 6-DOF pose and velocity evidence;
- center-of-gravity / center-of-buoyancy effects;
- ballast and trim state;
- added mass and hydrodynamic damping;
- current/environmental disturbance;
- depth and pressure;
- navigation covariance and dead-reckoning age;
- control-system response after a disturbance;
- sensor degradation and observability boundaries.

### Navigation and sensing

Surface operation can use GNSS, radar, cameras, sonar, inertial sensors, and conventional radio links. Submerged operation requires a different trust model, including combinations of inertial navigation, depth/pressure, Doppler velocity measurements, sonar/acoustic observations, and periodic absolute fixes when available.

ETS should record not merely a position value, but the source, reference frame, contributing sensors, uncertainty, last absolute fix, and elapsed navigation interval.

### Ranger Surface Relay Buoy

A future **Ranger Surface Relay Buoy (RSRB)** is planned as a civil research communications and evidence bridge for submerged Ranger operations.

The intended high-level chain is:

`Submerged Ranger → underwater link → RSRB → surface GNSS/time → RF/cellular/satellite path → ETS Gateway`

The relay buoy should be an evidence node rather than a transparent repeater. Research topics include:

- buoy identity;
- GNSS/time provenance;
- authenticated Ranger-to-buoy messages;
- receipt evidence;
- custody continuity across the air-water boundary;
- intermittent communications;
- preservation of Ranger's original signed evidence;
- distinction between vehicle state, buoy state, and Gateway state.

The public program will use open civil/AUV research patterns and will not depend on classified or operational submarine communication procedures.

### Marine VRX/R0 experiment

A particularly useful experiment is to apply the same characterized low-energy R0 disturbance across multiple physical regimes:

`dry test stand → floating surface → partially submerged → neutrally buoyant/submerged`

The objective is to measure how the same commanded actuation appears in:

- structural acceleration;
- angular motion;
- hydrodynamic response;
- control-system correction;
- navigation uncertainty;
- independently verifiable resulting-state evidence.

**Gate to advance:** terrestrial Ranger qualification first, then shallow-water recovery-safe testing, then progressive underwater autonomy only after buoyancy, trim, leak detection, navigation, communications, and fail-safe behavior are characterized.

---

## Phase 9 — Fleet, federation, compliance, and Evidence Exchange

**Primary objective:** scale from individual evidence-producing systems to interoperable evidence ecosystems.

Future work includes:

### Fleet

- multi-device identity;
- policy distribution;
- bounded fleet authority;
- cross-device custody;
- verifier-visible fleet state;
- coordinated evidence from multiple observers.

### ETS Compliance

- map evidence artifacts to defined control requirements;
- preserve the distinction between evidence and compliance judgment;
- support review packages without claiming that a cryptographic proof alone establishes legal or regulatory compliance.

### Evidence Exchange

- controlled evidence sharing across organizations;
- portable verification bundles;
- selective disclosure;
- federation and witness models;
- independent verifier interoperability;
- dispute and revocation semantics;
- provenance-preserving cross-domain exchange.

**Gate to advance:** evidence must remain independently verifiable after crossing administrative, organizational, device, and transport boundaries.

---

## Cross-cutting research tracks

These tracks apply across the roadmap rather than belonging to one phase:

- Evidence Object Model and Evidence Graph Model;
- provenance and epistemic boundaries;
- consequence custody;
- source independence and claim genealogy;
- cryptographic agility and key lifecycle;
- trusted time and clock quality;
- formal methods and reproducibility;
- adversarial qualification;
- omission and fork detection;
- privacy and selective disclosure;
- human governance and dispute handling;
- research publication and dissertation work;
- patent/IP preparation;
- standards alignment for AI agents, identity, Zero Trust, and evidence systems.

---

## What we will publish as the program matures

Public rollout should favor evidence over announcements. As stages mature, the project intends to publish selected:

- architecture documents;
- protocol and schema revisions;
- verifier examples;
- synthetic test vectors;
- qualification results;
- reproducible experiments;
- failure findings;
- threat models;
- Evidence Architecture lectures/manual material;
- Ranger and cyber-physical research results;
- research papers and dissertation artifacts.

Some implementation, security, customer, infrastructure, or IP-sensitive details may remain private even when the architectural result is public.

## What this roadmap does not promise

This document is not a release schedule, procurement commitment, safety certification, legal assurance, or statement that every named capability currently exists as a deployable product.

The ETS program is intentionally evidence-gated. A capability moves forward when its claims can be tested, its assumptions are visible, its failures can be recorded, and an independent party can verify the evidence that supports the claimed result.

That principle applies to everything from a Microsoft 365 event to an AI agent action to a Ranger actuator moving a physical machine.
