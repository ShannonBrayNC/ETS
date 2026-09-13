# ETS Public Roadmap — Current Status

**Program:** Lantern Protocol — Evidence Transparency System (ETS)  
**Status date:** September 13, 2026  
**Purpose:** Public-facing view of what exists now, what is being qualified, what remains research, and what is intentionally future work.

This document is a status companion to [`PUBLIC_ROADMAP.md`](PUBLIC_ROADMAP.md). It is intentionally evidence-gated. Repository artifacts, executable reference implementations, qualification documents, and completed experiments count as progress; plans and architecture alone do not count as deployed capability.

> **Status rule:** implemented is not the same as qualified; qualified is not the same as production-ready; cryptographic integrity is not the same as semantic truth or complete observation.

## Status vocabulary

| Status | Meaning |
|---|---|
| **Development** | Active implementation exists, but the supported production boundary is not established. |
| **Qualification** | The implementation or architecture is being tested against explicit gates, failure modes, identity, durability, deployment, or evidence requirements. |
| **Research** | Executable or documented research exists, but the work is not being represented as a deployable product. |
| **Future** | Direction is defined, but prerequisite gates or implementation are intentionally incomplete. |
| **Pilot-ready candidate** | A bounded pilot profile exists, but the specific physical/live environment still requires qualification. |

No item in this document is represented as Generally Available unless a separate release artifact explicitly says so.

---

# Executive status map

| Product / function | Current position | What exists now | Next meaningful gate |
|---|---|---|---|
| **ETS Protocol / Core** | **Development — alpha foundation** | Canonical hashing, append-only log, Merkle proofs, APIs, authentication profiles, persistence options, signing and proof verification paths, formal/reproducibility artifacts | Freeze and qualify the supported protocol/runtime boundary; complete deployment-owner and production hardening gates |
| **Evidence Object v1** | **Development** | Proposed normative contract, schemas, implementation models, migration compatibility path, examples, Ranger/VRX integrations | Stabilize canonical signing/verifier semantics and promote from proposed engineering specification to qualified core contract |
| **ETS Verify / Verifier** | **Development — usable reference implementation** | CLI/SDK verification, event/inclusion/consistency/bundle/tree-head checks, certificates/reports, retained-checkpoint research | Cross-implementation/external reproduction and release qualification of the verifier contract |
| **ETS Edge** | **Development + Qualification** | Edge runtime components, durable local demo, device identity, protected ingress, bounded queues, upstream synchronization, Docker/virtual-demo packaging, Azure private-origin work | Complete repeatable live/virtual qualification and define supported pilot profile |
| **ETS Gateway** | **Development + Qualification** | Architecture, threat model, profile, hosted runtime, Azure infrastructure, identity/authorization controls, durable relay/recovery work | Complete migration/live qualification and prove durable source-to-evidence-to-verifier behavior without broadening trust boundaries |
| **Microsoft 365 connector** | **Qualification** | SharePoint/Graph/Purview-related connector code, workload-identity qualification, lifecycle/reconciliation logic, source-to-proof tooling, migration gates | Complete bounded live soak/cross-tenant migration qualification and retain repeatable source-to-proof evidence |
| **ETS AI Witness** | **Development + Qualification** | v1 digest-first reference implementation, models/service/signing, chaining, durable-queue work, architecture/threat model, pilot appliance profile and candidate BOM | Qualify an isolated pilot appliance/runtime against external consequence and resulting-state evidence requirements |
| **ETS Vault** | **Development + Qualification** | Backend-neutral software implementation, write-once semantics, retention extension, legal hold, dual-control disposition, integrity contracts, v1 qualification contract | Qualify a real retention backend/appliance and demonstrate independent preservation/retrieval under failure |
| **ETS Black Box** | **Development + Qualification** | Software reference implementation, rolling incident-window model, durable state contracts, v1 specification, architecture and threat model | Qualify the physical/appliance survivability boundary and independent post-incident retrieval |
| **Provenance / ETS Mobile** | **Development + Qualification — private implementation** | Private iOS/Android architecture and implementation program, provenance-at-origin rules, identity/attestation, offline continuity, transformation lineage, Gateway/Verify integration design | Physical Android Phase 1A qualification; then bounded pilot profile |
| **Ranger R0** | **Research — executable software reference, pre-vehicle** | Deterministic mobility simulator, fail-closed safety contract, authority lifecycle, signed local custody, checkpoint/publication evidence profiles, cyber-physical observability model, Decision Event schema | Build and qualify the physical terrestrial R0 while preserving the same evidence contracts; prove end-to-end consequence custody on real hardware |
| **VectorRail / VRX R0** | **Research — executable evidence path, pre-hardware** | Pre-hardware laboratory acceptance spec, executable acceptance/evidence/verifier artifacts, schemas, release validation baseline, consequence-custody demonstration | Construct the low-energy captive R0 apparatus and collect repeatable measured physical data under the acceptance protocol |
| **Ranger Marine** | **Future research — architecture defined** | Public research sequence, 6-DOF evidence requirements, ballast/trim/navigation uncertainty model, staged surface/submerged concept | Terrestrial Ranger must be fully characterized first; then dry marine instrumentation and recovery-safe flotation qualification |
| **Ranger Surface Relay Buoy (RSRB)** | **Future research** | High-level civil/AUV relay and evidence-custody architecture | Define protocol/profile after Marine Ranger navigation and communications requirements are experimentally bounded |
| **ETS Fleet** | **Development + Qualification** | Enrollment/presence/control-plane implementation profiles, TPM/DPS identity work, private Azure substrate and Entra qualification tracks | Complete live private control-plane qualification and physical device identity/presence pilot without claiming unverified production activation |
| **ETS Compliance** | **Development — software reference** | COMP-C0 deterministic control-to-evidence evaluation, models/service, architecture, threat model, v1 spec | Add qualified framework/control-pack interchange and prove policy-version/review reproducibility while preserving evidence-vs-judgment boundary |
| **Evidence Exchange** | **Future — prerequisites under construction** | Evidence Object model, portable proof concepts, verifier/federation primitives, cross-domain provenance concepts | Define the Exchange protocol, selective-disclosure/federation rules, revocation/dispute semantics, and independent cross-organization conformance tests |
| **ETS Adversarial Qualification (EAQ)** | **Research baseline** | Program definition and research roadmap for authorized evidence-aware adversarial qualification | Convert selected research invariants into repeatable release gates backed by measured evidence |
| **Formal methods / reproducibility** | **Active research** | TLA+ models, Alloy causal model, theorem/traceability/reproducibility artifacts, deterministic experiment packaging | Expand symbolic/model checking and refinement coverage; continue distinguishing modeled properties from production claims |
| **Evidence Architecture research / dissertation** | **Active research** | Epistemic provenance, source independence, observability, consequence custody, mathematical appendices, experiment and contribution ledgers, application dossier material | Physical experiments, independent reproduction/external validation, peer review, and continued prior-art narrowing |

---

# Detailed status by roadmap phase

## Phase 0 — ETS Core and independent verification

### ETS Protocol / Core

**Current status: Development — alpha/reference foundation.**

Already present:

- deterministic canonical JSON hashing;
- append-only evidence-event handling;
- Merkle inclusion and consistency verification paths;
- local API/SDK/CLI surfaces;
- durable SQLite testing and additional hosted-storage work;
- tenant/workspace scoping;
- local and production-oriented authentication modes;
- signing profiles and tree-head verification;
- external-anchor experiments;
- research reproducibility and formal-system artifacts.

**Not yet claimed:** a generally available production trust service.

**Next gate:** stabilize the supported protocol/runtime boundary and complete production deployment, key-management, durability, and operational qualification.

### Evidence Object v1

**Current status: Development.**

The repository contains the proposed v1 normative contract, schemas, implementation models, examples, and an additive migration path from EvidenceEvent. Ranger/VRX work is already exercising the Evidence Object boundary.

**Next gate:** freeze canonical signing, identifier, projection, and independent-verifier behavior without rewriting historical transparency-log semantics.

### ETS Verify / Verifier

**Current status: Development — functional reference implementation.**

Already present:

- event hash verification;
- inclusion-proof verification;
- consistency-proof verification;
- bundle verification;
- tree-head checks;
- certificate/report generation;
- offline/portable verification workflows;
- retained-checkpoint and federation research.

**Next gate:** external/cross-implementation reproduction using frozen vectors and a clearly versioned trust/profile contract.

---

## Phase 1 — ETS Edge

**Current status: Development + Qualification.**

Already present:

- near-source Edge software components;
- device identity material;
- protected ingress;
- durable local SQLite demo path;
- bounded queue behavior;
- offline/upstream synchronization behavior;
- Docker packaging;
- virtual Edge demonstration assets;
- Azure private-origin infrastructure/handoff work.

This is beyond a paper architecture, but it is not yet a generally available supported appliance.

**Next gate:** repeatable bounded live qualification demonstrating local durability, recovery, identity, synchronization, and verifier-visible custody after disruption.

---

## Phase 2 — ETS Gateway and enterprise connectors

### ETS Gateway

**Current status: Development + Qualification.**

Already present:

- architecture and threat model;
- normative/profile work;
- hosted runtime implementation;
- durable relay/state work;
- Azure infrastructure definitions;
- managed identity / authorization boundaries;
- migration and live-qualification tooling;
- source health, replay, reconciliation, and evidence packaging concepts.

The Gateway G0 material exists and later live/migration work has moved beyond G0 architecture, but the public status should remain **qualification**, not production.

**Next gate:** prove the post-migration/live runtime repeatedly with durable state, least privilege, recovery, and independent proof continuity.

### Microsoft 365 connector

**Current status: Qualification.**

Already present:

- SharePoint source retrieval work;
- Graph lifecycle/subscription handling;
- Purview activity discovery/retrieval distinctions;
- workload-identity qualification;
- bounded permissions such as site-scoped access patterns;
- pre-soak and migration gates;
- source-to-proof orchestration.

**Next gate:** complete a bounded live soak and preserve reproducible evidence showing the exact chain from source retrieval through Gateway creation/custody to independent verification.

---

## Phase 3 — ETS AI Witness

**Current status: Development + Qualification.**

Already present:

- digest-first witness event contracts;
- v1 reference implementation;
- model/input/output/tool/policy commitment structures;
- session chaining and signing;
- durable queue work;
- signer-provider abstraction;
- ETS projection;
- architecture and threat models;
- pilot appliance profile;
- candidate reference hardware/BOM.

**Next gate:** operate the Witness as an isolated pilot boundary and demonstrate that externally claimed consequences are corroborated by the target/resulting state rather than solely by the AI's own transcript.

---

## Phase 4 — ETS Vault and Black Box

### ETS Vault

**Current status: Development + Qualification.**

Already present:

- backend-neutral preservation core;
- write-once service semantics;
- SHA-256 integrity binding;
- retention extension;
- compliance-mode non-downgrade rules;
- legal holds;
- dual-control disposition;
- v1 implementation/appliance qualification contract.

**Next gate:** qualify a real immutable/retention-governed backend and demonstrate independent retrieval/integrity after primary runtime failure.

### ETS Black Box

**Current status: Development + Qualification.**

Already present:

- software reference implementation;
- rolling observation-window semantics;
- incident trigger and sealed-segment concepts;
- durable reference stores;
- strict data contracts;
- architecture and threat model;
- physical-appliance qualification contract.

**Next gate:** qualify actual hardware/storage survivability and prove post-incident recovery without assuming the monitored machine remains trustworthy or available.

---

## Phase 5 — Provenance / ETS Mobile

**Current status: Development + Qualification — private implementation.**

The mobile product is now branded **Provenance** while retaining ETS Mobile implementation identifiers internally.

Already present in the private program:

- provenance-at-origin architecture;
- iOS/Android capture-client work;
- device/workload identity and attestation;
- offline evidence continuity;
- secure local state/key handling;
- derivation and AI-transformation lineage;
- Gateway/Verify integration design;
- Black Box corroboration path;
- adversarial/conformance planning.

**Next gate:** physical Android Phase 1A qualification. Until that passes, the software should not be represented as production-qualified mobile evidence capture.

---

## Phase 6 — Ranger R0

**Current status: Research — strong executable software reference, physical platform not yet qualified.**

Already present:

- R0 architecture and mission definition;
- fail-closed motion/safety contract;
- deterministic mobility simulator;
- authority lifecycle evidence;
- signed local source custody;
- cross-boot continuity work;
- retained checkpoint and trusted-time profiles;
- publication/custodian key lifecycle work;
- immutable-publication and AWS verification research;
- cyber-physical observability model;
- bounded identity/epistemic-state work;
- Ranger Decision Event schema;
- consequence-custody integration work.

**Critical distinction:** this is substantive software/research progress, but it is not evidence that a physical Ranger chassis has passed mobility, safety, or consequence qualification.

**Next gate:** build the terrestrial R0 and run the same evidence chain against measured physical actuator response and resulting state.

---

## Phase 7 — VectorRail / VRX

**Current status: Research — executable acceptance/evidence system, pre-hardware laboratory stage.**

Already present:

- pre-hardware laboratory acceptance specification;
- VRX acceptance schema;
- qualified/not-qualified deterministic fixtures;
- acceptance implementation;
- acceptance evidence projection;
- independent verifier;
- clean-room verifier contract;
- v0.1.0 validation baseline;
- executable end-to-end consequence-custody research artifact;
- proposed external-validation protocol.

**Next gate:** build the low-energy captive R0 apparatus and replace simulated/deterministic trial observations with calibrated current, motion, vibration, timing, thermal, and resulting-state measurements.

No larger VRX variant should advance merely because it can be designed. Scaling should follow measured Ranger dynamics, safety, structural response, and evidentiary value.

---

## Phase 8 — Ranger Marine and RSRB

### Ranger Marine

**Current status: Future research — architecture defined, intentionally blocked by terrestrial Ranger.**

Defined research areas:

- dry marine instrumentation;
- flotation, trim, buoyancy, and ballast;
- shallow tethered testing;
- surface operation;
- controlled submergence;
- submerged navigation;
- 6-DOF state/velocity evidence;
- added mass and hydrodynamic damping;
- navigation uncertainty/covariance;
- surface relay communications;
- controlled cross-medium VRX/R0 disturbance experiments.

**Next gate:** terrestrial Ranger must first become an operational, measured baseline. After that: dry instrumentation, recovery-safe flotation, and shallow tethered qualification.

### Ranger Surface Relay Buoy (RSRB)

**Current status: Future research.**

Defined role:

`Submerged Ranger → underwater link → RSRB → surface GNSS/time → RF/cellular/satellite → ETS Gateway`

The RSRB is intended to preserve identity, receipt evidence, original Ranger signatures, time/location provenance, and custody transitions rather than function as an opaque repeater.

**Next gate:** derive the actual message, custody, positioning, and communications profile from Marine Ranger's measured navigation/communications requirements.

---

## Phase 9 — Fleet, Compliance, and Evidence Exchange

### ETS Fleet

**Current status: Development + Qualification.**

Already present:

- device enrollment/profile work;
- physical TPM qualification profiles;
- Azure DPS identity work;
- signed device presence runtime;
- durable administration/control-plane work;
- private Azure substrate qualification;
- Entra bootstrap and authorization qualification;
- protected Front Door/private-origin work;
- physical-pilot preparation artifacts.

**Next gate:** complete live private Fleet qualification and then execute a bounded physical-device pilot with verifiable enrollment, presence, policy, and custody. No public status should imply that an unqualified live control plane is already production active.

### ETS Compliance

**Current status: Development — software reference implementation.**

Already present:

- COMP-C0 deterministic evaluation path;
- strict control/evidence models;
- policy-bound service implementation;
- architecture;
- threat model;
- v1 specification;
- explicit evidence-vs-compliance-judgment boundary.

**Next gate:** qualify framework/control-pack import/export and reproducible policy-version evaluation against independently verified evidence references.

### Evidence Exchange

**Current status: Future — enabling primitives exist, distinct Exchange implementation does not yet constitute a qualified product.**

Prerequisites already under construction:

- Evidence Object semantics;
- portable verifier/proof bundles;
- verifier/federation work;
- cross-device custody;
- source ancestry/provenance;
- selective-disclosure research;
- dispute/revocation concepts.

**Next gate:** define a versioned Exchange protocol and demonstrate that evidence remains independently verifiable after crossing organization, transport, and administrative boundaries.

---

# Cross-cutting functions

| Function | Current status | Current position |
|---|---|---|
| **Cryptographic integrity / canonicalization** | Development, broadly implemented in core/reference paths | Foundation is strong; production key lifecycle and supported profiles still require qualification |
| **Merkle proofs / transparency log** | Development, implemented | Reference functionality exists; consistency/federation scope remains bounded and must not be overstated |
| **Identity / device enrollment** | Development + Qualification | Core, Edge, Gateway, Fleet, Mobile and Ranger each have identity work; physical/production attestation remains profile-specific |
| **Trusted time / clock quality** | Development + Research | Multiple profiles capture time quality and retained receipts; external time does not automatically prove event truth |
| **Offline continuity / replay / recovery** | Development + Qualification | Implemented across Edge/Gateway-related paths and designed into Mobile/Ranger; live failure qualification remains important |
| **Consequence custody** | Research advancing rapidly | Ranger/VRX provide executable digital-to-physical evidence chains; real physical experiments remain the major next step |
| **Epistemic provenance / observability** | Active research | Formalized in dissertation/Ranger materials; now needs more empirical validation and external review |
| **Formal methods** | Active research | TLA+, Alloy, theorem/traceability artifacts exist; no claim of complete system proof |
| **Adversarial qualification (EAQ)** | Research baseline | Program and roadmap exist; selected tests still need promotion into release gates |
| **Privacy / minimization / selective disclosure** | Development + Research | Present in product profiles and architecture; Exchange/mobile use cases will require deeper qualification |
| **Standards alignment** | Active research | AI agent control, Zero Trust, identity, provenance and evidence standards are being mapped; alignment is not certification |
| **Research publication / dissertation** | Active research | Large technical corpus, experiment ledgers and application material exist; independent reproduction and peer review remain important maturity gates |
| **Patent/IP preparation** | Active preparation | Technical disclosure/prior-art/claim-support work exists; public release must continue to observe the public/private boundary |

---

# What is closest to public demonstration now?

The strongest near-term public demonstrations are the areas where implementation and independent verification already meet:

1. **ETS Core + Verify** — create a bounded evidence record, produce proof material, verify it independently, and show the exact limits of the claim.
2. **ETS Edge virtual path** — demonstrate near-source capture, local durability, disconnection/recovery, and later verification without pretending the demo is a production appliance.
3. **Gateway + Microsoft 365** — once the current live qualification/migration gate is complete, show source retrieval → evidence creation → custody → verifier as an enterprise example.
4. **AI Witness** — demonstrate digest-first AI/agent observation and the distinction between an agent's reported action and externally observed consequence.
5. **Vault / Black Box software references** — demonstrate preservation and incident-window semantics while clearly identifying the remaining physical/backend qualification boundary.
6. **Ranger / VRX software evidence chains** — publish the research contracts, executable verifier paths, and simulation results now; publish physical results only after calibrated hardware experiments exist.

---

# What is intentionally not ready to claim?

The following should remain explicit in the public rollout:

- ETS is not yet represented as a generally available production trust service.
- A passing software/reference test is not a physical-appliance qualification.
- Ranger is not yet a qualified physical autonomous vehicle.
- VRX R0 is still pre-hardware even though its acceptance/evidence/verifier path is executable.
- Ranger Marine and RSRB are architectural research tracks, not current hardware products.
- Evidence Exchange is not yet a qualified interoperable service.
- ETS Compliance evaluates evidence against explicit policy; it does not automatically certify legal or regulatory compliance.
- AI Witness records bounded observations; it does not make an AI system the unquestioned historian of its own actions.
- Signed evidence proves integrity/provenance within stated assumptions; it does not automatically prove objective truth or complete observation.

---

# Public rollout sequence

For public communication, the clearest progression is:

**Now:** Core, Verify, Edge, Gateway/M365 qualification, AI Witness, Vault/Black Box reference implementations, Mobile/Provenance development, Fleet qualification, Compliance reference implementation, Ranger/VRX research artifacts.

**Next:** bounded live demonstrations, external verification, M365 source-to-proof qualification, physical Mobile qualification, terrestrial Ranger hardware, physical VRX R0 measurements.

**Then:** Ranger autonomy/consequence-custody qualification, physical Black Box/Vault appliance/backends, Fleet physical pilots, Compliance framework interchange, broader enterprise pilots.

**Later:** Ranger Marine, RSRB, cross-medium 6-DOF evidence experiments, Evidence Exchange, and broader federation/interoperability.

The ordering is intentionally evidence-driven rather than marketing-driven: each layer should earn the right to support the next one.