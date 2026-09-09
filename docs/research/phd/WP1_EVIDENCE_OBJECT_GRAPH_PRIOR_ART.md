# WP1 — Evidence Object and Evidence Graph Prior-Art Qualification

**Status:** first-pass literature/prior-art qualification  
**Date:** 2026-09-08  
**Contributions:** EA-C001, EA-C002  
**Record type:** retrospective qualification of previously documented candidate contributions

## Research-integrity boundary

This document does not claim that the Evidence Object or Evidence Graph is novel merely because ETS implements or documents it. It identifies adjacent prior art, separates overlapping ideas from candidate differentiators, and records the work still required before either contribution can be promoted from `candidate` to `supported`.

The relevant question is not whether prior systems contain provenance, signatures, event histories, graphs, attestations, or tamper-evident logs. They clearly do. The research question is whether ETS/Evidence Architecture contributes a defensible combination or formalization that is materially different from those systems and can be evaluated independently.

## EA-C001 — Evidence Object

Candidate claim from the contribution ledger:

> ETS provides a bounded Evidence Object model for independently evaluating identity, integrity, provenance, custody, and declared verification context while separating those properties from semantic truth.

### Closest prior-art families

#### W3C PROV

W3C PROV is a domain-agnostic provenance model centered on entities, activities, agents, responsibility, derivation, usage, generation, time, specialization, collections, and provenance bundles. It explicitly supports interchange and validation of provenance descriptions.

**Overlap with EA-C001:**
- provenance of entities and activities;
- agent/responsibility relationships;
- derivation and generation;
- time and event relationships;
- domain-independent representation;
- provenance of provenance through bundles.

**Candidate distinction requiring proof:** an ETS Evidence Object is intended to be an independently addressable evidentiary envelope whose verification semantics explicitly separate byte integrity, signer/source identity, provenance, custody, policy/standing context, epistemic state, and unsupported semantic truth. W3C PROV is therefore substantial prior art for provenance representation, but it does not by itself establish that the ETS bounded verification envelope is redundant.

This distinction remains **candidate**, not established novelty.

#### Remote Attestation (IETF RATS)

RFC 9334 defines Attester, Verifier, Relying Party, Evidence, Attestation Results, Endorsements, Reference Values, and appraisal policies. Evidence contains claims about a target environment and is appraised by a verifier.

**Overlap:**
- explicit evidence and verifier roles;
- appraisal policy;
- claims rather than assumed truth;
- reference values and endorsements;
- separation of evidence from relying-party decision.

**Candidate distinction requiring proof:** EA-C001 is broader than device/platform attestation and attempts to preserve evidence for arbitrary digital, organizational, AI, and cyber-physical claims, including custody and consequence relationships. The research contribution cannot be stated merely as “evidence plus verifier,” because RATS already provides that architecture in attestation.

#### in-toto / software supply-chain attestations

in-toto records signed metadata for supply-chain steps, including authorized functionaries, commands, materials, products, and verification against a signed layout.

**Overlap:**
- signed evidence for performed actions;
- actor/functionary authorization;
- artifact digests;
- declared workflow expectations;
- verification of materials/products and step execution.

**Candidate distinction requiring proof:** Evidence Objects are intended to be domain-neutral and to preserve richer bounded-claim semantics, policy/standing, epistemic state, custody, and consequences beyond software supply-chain steps. Domain generality alone is not sufficient novelty; the specific semantics and measurable verification benefit must be demonstrated.

#### Transparency / tamper-evident logs

Certificate Transparency (RFC 9162) provides append-only Merkle logs, inclusion proofs, consistency proofs, signed timestamps, and mechanisms for detecting certain log misbehaviors.

**Overlap:**
- cryptographic commitments;
- inclusion and consistency verification;
- append-only history;
- independent monitoring/auditing.

**Candidate distinction requiring proof:** an Evidence Object is not merely a transparency-log leaf. ETS attempts to bind an object to evidence semantics and later evaluate multiple claim dimensions. CT is especially important prior art against any claim that Merkle inclusion, append-only logging, or independent log verification is itself novel.

#### Event sourcing

Event sourcing records application state changes as a sequence of events and can reconstruct historical state.

**Overlap:**
- historical reconstruction;
- event sequence as durable system history;
- derived current state from prior events.

**Candidate distinction requiring proof:** event history does not inherently provide independent cryptographic verification, source authority, custody, policy standing, or an epistemic claim boundary. Conversely, Evidence Architecture must not claim event reconstruction itself as novel.

### EA-C001 provisional gap statement

The defensible research gap, if supported by broader literature and evaluation, is narrower than “a structured provenance record.” A candidate gap is:

> Existing provenance, attestation, transparency-log, supply-chain, and event-history systems each strongly address subsets of provenance, integrity, appraisal, authorization, or reconstruction. EA-C001 investigates whether a domain-neutral Evidence Object can make those assurance dimensions independently inspectable while explicitly preserving epistemic and semantic nonclaims, historical policy/standing context, and portability across trust boundaries.

### EA-C001 novelty hazards

Do **not** claim novelty for:
- provenance records;
- signed metadata;
- hash-addressed objects;
- Merkle inclusion;
- append-only logs;
- event histories;
- attester/verifier separation;
- policy-based appraisal;
- chain of custody as a general concept.

Potentially researchable differentiators:
- explicit verification claim vector rather than universal `verified`;
- first-class epistemic absence/unknown/indeterminate states in the evidence envelope;
- historical standing/policy evidence bound to consequential events;
- portability of claim boundaries and nonclaims with the object;
- composition from digital evidence into consequence custody without equating command with result.

## EA-C002 — Evidence Graph

Candidate claim from the contribution ledger:

> Typed graph relationships can make derivation, custody, authority, observation, decision, action, and consequence claims separately inspectable and verifiable without asserting truth merely from graph membership.

### Closest prior-art families

#### W3C PROV graph semantics

PROV already represents rich relationships among entities, activities, agents, derivations, generation, usage, attribution, association, delegation, and temporal events. It includes formal constraints and semantics.

This is the closest baseline and prevents any broad claim that a typed provenance graph is novel.

**Candidate distinction requiring proof:** Evidence Graph edges are treated as evidentiary claims whose epistemic status, producer, integrity, dependencies, and verification status may themselves need preservation. The intended graph also extends through policy/authority, decision, command/action, consequence, and resulting observation while refusing to infer semantic truth or causality merely from graph topology.

A rigorous mapping to PROV relations is required. New ETS edge types should be classified as:
1. direct PROV equivalents;
2. specializations expressible through PROV qualification;
3. profile/domain extensions;
4. genuinely missing semantics, if any.

#### in-toto workflow/link relationships

in-toto links materials, execution steps, products, functionaries, and expected workflow layout. It is strong prior art for verifiable step-to-artifact relationships.

**Candidate distinction requiring proof:** EA-C002 attempts to generalize beyond a declared software supply chain into heterogeneous evidence relationships including observation, inference, authority, policy, decision, actuation, consequence, contradiction, correction, and epistemic absence.

#### Event/dependency graphs

Event sourcing and distributed tracing/event systems can represent causal-looking or dependency sequences. These are prior art against claims that event linkage or reconstruction graphs are new.

The research distinction must focus on evidentiary semantics, verification boundaries, and explicit refusal to infer causality from mere adjacency or asserted relationships.

### EA-C002 provisional gap statement

A candidate research gap is:

> Existing provenance and workflow models provide rich typed dependency relationships. EA-C002 investigates whether treating each relationship as a separately attributable and verifiable evidentiary claim—while preserving epistemic state, authority/policy dependencies, consequence custody, contradictions, and explicit noncausality—improves independent reconstruction of consequential digital and cyber-physical events.

### EA-C002 novelty hazards

Do **not** claim novelty for:
- provenance graphs;
- entity/activity/agent graphs;
- typed edges;
- derivation graphs;
- workflow graphs;
- causal or dependency graphs generally;
- graph-based chain of custody generally.

Potentially researchable differentiators:
- edge-as-claim semantics with independent provenance and verification;
- identity as a staged claim graph rather than a single recognition result;
- explicit contradiction and epistemic-absence representation;
- inference dependency and shared-source detection for corroboration;
- decision -> requested action -> accepted/executed action -> consequence -> result-observation decomposition;
- consequence-custody graph semantics across digital and physical boundaries.

## Comparative matrix

| Prior-art family | Provenance | Signed/integrity evidence | Typed relationships | Policy/authority | Independent verifier/appraisal | Epistemic nonclaims | Consequence/result separation | Primary implication |
|---|---|---|---|---|---|---|---|---|
| W3C PROV | strong | external/extension | strong | responsibility/delegation; extensible | validation, not ETS-style assurance vector | not central | extensible, not central | closest graph/provenance baseline |
| RATS | attestation-focused | architecture supports protected evidence | role/message relationships | appraisal policy | strong | claim/appraisal boundaries | not general purpose | closest verifier/evidence architecture baseline |
| in-toto | supply-chain provenance | strong signed metadata | strong workflow links | authorized functionaries/layout | strong workflow verification | limited domain semantics | products recorded, not general consequence custody | closest signed workflow evidence baseline |
| Certificate Transparency | log provenance/history | strong Merkle/signature mechanisms | log inclusion/consistency | log policy ecosystem | strong auditing/monitoring | narrow protocol claims | no | defeats novelty claims around append-only/Merkle verification |
| Event sourcing | event history | implementation-dependent | sequence/dependency | application-specific | not inherent | not inherent | state reconstruction, not evidentiary consequence custody | defeats novelty claims around historical reconstruction |
| ETS EA-C001/C002 candidate | domain-neutral evidence | intended multi-dimensional verification | evidence relationships as claims | historical policy/standing | intended independent verification | explicit | explicit | novelty must be shown in composition/semantics/evaluation |

## Falsification criteria

EA-C001 should be revised or narrowed if prior work is found that already defines, in a substantially equivalent domain-neutral model, all of the following as integrated semantics:
1. portable evidence envelopes;
2. independently verifiable integrity/source/provenance/custody;
3. historical policy/standing context;
4. explicit epistemic states and nonclaims;
5. consequence/result evidence separation.

EA-C002 should be revised or narrowed if an existing provenance model already provides substantially equivalent semantics for:
1. edges as separately attributable evidentiary claims;
2. epistemic/contradiction state on relationships;
3. authority/policy/decision/action/consequence/result relationships;
4. shared-source dependence and inference lineage;
5. independent verification without truth/causality inference from graph membership.

## Next literature slice

The first pass establishes that broad provenance/object/graph novelty claims are untenable. Before promotion, WP1 should continue with peer-reviewed literature in:

- scientific workflow provenance and provenance semirings;
- database provenance / why- and where-provenance;
- digital-forensics chain-of-custody models;
- secure audit logs and forward-integrity logging;
- authenticated data structures and transparency systems beyond CT;
- knowledge graphs and claim/evidence graphs;
- trust management and authorization provenance;
- cyber-physical provenance and safety-case evidence;
- AI provenance/model lineage and machine-action accountability.

## Provisional disposition

- **EA-C001:** remains `candidate`; candidate gap narrowed and made defensible enough for deeper review.
- **EA-C002:** remains `candidate`; W3C PROV is confirmed as the primary comparison baseline and a formal relation-by-relation mapping is required.

No contribution is promoted by this document.

## Primary sources reviewed in this pass

- W3C PROV family: PROV-DM/Primer, Constraints, Semantics, Overview.
- IETF RFC 9334, Remote ATtestation procedureS (RATS) Architecture.
- IETF RFC 9162, Certificate Transparency Version 2.0.
- in-toto specification and metadata model.
- Martin Fowler, Event Sourcing (2005), used only as a canonical architecture reference rather than peer-reviewed novelty evidence.
