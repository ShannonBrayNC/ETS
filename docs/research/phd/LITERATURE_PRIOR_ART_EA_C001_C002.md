# Prior-Art Qualification — EA-C001 Evidence Object and EA-C002 Evidence Graph

Status: working literature qualification, not a novelty determination.

This document establishes the first doctoral prior-art comparison for ETS candidate contributions `EA-C001` and `EA-C002`. It is deliberately conservative: overlap with established work is recorded explicitly, and any ETS-specific distinction remains a **candidate gap** until tested against broader peer-reviewed literature and independent academic review.

## Research questions

- `RQ1`: What information must an evidence unit expose so an independent verifier can evaluate bounded claims about identity, integrity, provenance, custody, and verification context without treating integrity as semantic truth?
- `RQ2`: How can relationships among evidence units represent derivation, observation, authority, decision, action, custody, and consequence while keeping those claim types distinguishable?
- `RQ3`: Which properties can be established cryptographically or procedurally, and which remain external assertions or trust assumptions?

## Method

This first pass uses primary specifications and authoritative standards pages as boundary-setting sources. It is not a systematic review. A later scholarly pass must add peer-reviewed provenance, digital-forensics, tamper-evident logging, graph, attestation, and evidence-management literature and record search databases, terms, dates, inclusion/exclusion criteria, and citation chaining.

For each comparison, we record:

1. what the existing work actually provides;
2. where it overlaps ETS;
3. what it does **not** establish for ETS;
4. the candidate research gap that remains to be tested.

## Comparison set

### W3C PROV

Primary source: W3C PROV Model Primer, <https://www.w3.org/TR/prov-primer/>.

W3C PROV defines a general provenance data model centered on entities, activities, and agents, with relations describing how things were generated, used, derived, attributed, associated, and influenced. It is intended for interoperable provenance representation rather than as a complete cryptographic evidence-verification protocol.

**Overlap with ETS**

- provenance as structured relationships rather than prose;
- actors/agents and activities/processes;
- derivation and generation relationships;
- graph-oriented representation of provenance history.

**Boundary / unresolved distinction**

W3C PROV establishes vocabulary and semantics for provenance representation. It does not, by itself, establish that a provenance assertion is authentic, complete, independently observed, cryptographically bound to an event, or preserved in an append-only evidence history. ETS therefore must not claim novelty merely for using a provenance graph.

**Candidate ETS gap**

The candidate distinction for `EA-C002` is the use of typed evidence relationships whose verification result preserves the difference between cryptographically/procedurally supported relationships and externally asserted semantics, especially across observation → inference → decision → authority → action → consequence boundaries.

### Certificate Transparency / append-only Merkle logs

Primary source: RFC 6962, Certificate Transparency, <https://www.rfc-editor.org/rfc/rfc6962.html>.

Certificate Transparency demonstrates publicly auditable append-only logs, Merkle inclusion/consistency proofs, signed tree heads, and detection of conflicting log views without requiring blind trust in a log operator.

**Overlap with ETS**

- append-only evidence histories;
- Merkle inclusion and consistency proofs;
- externally comparable signed roots / heads;
- detection of equivocation or conflicting views.

**Boundary / unresolved distinction**

Certificate Transparency is specialized to certificate logging and does not attempt to model general evidentiary semantics, custody, authority, observation, action, or physical consequence. ETS must not claim novelty for append-only Merkle logging or consistency proofs.

**Candidate ETS gap**

For `EA-C001`, the candidate contribution is not the log mechanism but the composition of bounded evidence semantics with independently verifiable integrity/provenance context while explicitly refusing to infer real-world truth from inclusion. For `EA-C002`, the candidate question is how independently inspectable event relationships interact with append-only publication and cross-observer verification.

### in-toto

Primary sources: in-toto specification index, <https://in-toto.io/docs/specs/>; getting started and model overview, <https://in-toto.io/docs/getting-started/>.

in-toto protects software supply-chain integrity by defining an expected signed layout of authorized steps and collecting signed link metadata describing commands, materials, and products. Verification checks whether authorized functionaries performed expected steps and whether artifact rules were satisfied.

**Overlap with ETS**

- signed metadata about actions;
- actor/functionary identity and authorization;
- expected process/policy compared with observed metadata;
- chained artifacts and transformations;
- independent verification against declared rules.

**Boundary / unresolved distinction**

in-toto is a strong precedent for evidence about authorized transformations in a software supply chain. ETS cannot claim novelty for signed step metadata, actor authorization, or chained transformation evidence.

**Candidate ETS gap**

The ETS hypothesis is broader and claim-type-oriented: the same evidence architecture should distinguish observation, inference, authority, command, custody, and resulting state across software, AI, distributed, and cyber-physical domains. Whether that generalization is original or useful requires comparison with additional attestation and provenance systems.

### SLSA provenance

Primary source: SLSA Provenance v1.2, <https://slsa.dev/spec/v1.2/provenance>.

SLSA defines verifiable provenance for software artifacts, including where, when, and how an artifact was produced, with specialized build and source provenance profiles and attestation distribution requirements.

**Overlap with ETS**

- verifiable provenance statements;
- artifact identity and production context;
- producer/builder identity;
- verification of provenance against expectations;
- explicit distribution of attestations.

**Boundary / unresolved distinction**

SLSA is scoped primarily to software supply-chain provenance. ETS must not claim that verifiable artifact provenance is new.

**Candidate ETS gap**

For `EA-C001`, the candidate distinction is a general evidence unit that represents multiple bounded claim classes beyond build/source provenance. For `EA-C002`, the candidate distinction is a graph that composes heterogeneous evidence transitions, including consequence-state evidence, while preserving which edges are verified, asserted, or externally dependent.

### C2PA Content Credentials

Primary source: C2PA Content Credentials specification 2.4, <https://spec.c2pa.org/specifications/specifications/2.4/specs/ContentCredentials.html>.

C2PA provides cryptographically verifiable provenance for digital media through manifests, assertions, content bindings, signatures, and manifest relationships. Its specification distinguishes provenance and authenticity in the sense of verifiable, non-tampered provenance facts under a defined trust model.

**Overlap with ETS**

- signed assertions and manifests;
- binding metadata to digital content;
- provenance history across transformations;
- referenced prior manifests / ingredients;
- explicit trust-model dependence.

**Boundary / unresolved distinction**

C2PA is a major adjacent system and substantially narrows any broad ETS novelty claim around signed provenance objects. ETS must compare its Evidence Object semantics directly against C2PA manifests and attestations before asserting originality.

**Candidate ETS gap**

The remaining candidate distinction is evidence-type and consequence semantics outside media provenance: independent verification of observation, authority, decision/action, custody, and resulting-state claims across general distributed and cyber-physical systems, with explicit unsupported-assumption retention rather than a generic authenticity conclusion.

### NIST digital forensics and evidence management

Primary sources: NIST CSRC Digital Forensics glossary, <https://csrc.nist.gov/glossary/term/digital_forensics>; NIST Evidence Management, <https://www.nist.gov/forensic-science/interdisciplinary-topics/evidence-management>.

NIST definitions and guidance emphasize integrity preservation, chain of custody, validated methods/tools, repeatability, reporting, and evidence management that prevents compromise or degradation.

**Overlap with ETS**

- evidence integrity;
- chain/custody concerns;
- repeatability and validated verification procedures;
- separation of evidence handling from substantive interpretation.

**Boundary / unresolved distinction**

Digital forensics already treats custody, integrity, validation, and reproducibility as foundational. ETS cannot present those concepts themselves as novel.

**Candidate ETS gap**

The research question is whether those evidentiary principles can be made machine-verifiable and composable as first-class protocol objects across distributed/AI/cyber-physical systems while retaining explicit epistemic boundaries.

## Preliminary closest-work matrix

| Capability / property | W3C PROV | CT | in-toto | SLSA | C2PA | NIST forensics | ETS candidate |
|---|---|---|---|---|---|---|---|
| Structured provenance relationships | strong | narrow | step chain | artifact lineage | manifest lineage | procedural | candidate generalized typed graph |
| Cryptographic binding/signing | optional/outside core | strong | strong | attestation-dependent | strong | method-dependent | strong in implemented bounded surfaces |
| Append-only public consistency | no | strong | no | no | no general log requirement | no | implemented/bounded ETS log surface |
| Actor/authority representation | agent model | log operator/CA context | functionary authorization | builder/source actor | signer/claim generator | custodian/process | candidate explicit authority edge types |
| Custody as first-class concern | provenance-capable but not forensic custody protocol | no | no | no | limited provenance context | strong procedural | candidate machine-verifiable custody semantics |
| Observation vs inference distinction | representable but not verification-specific | no | no | no | assertion-dependent | investigative-method dependent | candidate explicit claim boundary |
| Decision → action → consequence chain | representable generically | no | software steps | build/source | media transformations | case-dependent | candidate typed cross-domain chain |
| Explicit unsupported-assumption retention | model-dependent | log scope clear | policy/layout scope | provenance scope | trust-model scope | expert/process scope | candidate verifier output discipline |
| Cyber-physical resulting-state evidence | generic representability | no | no | no | not primary scope | possible forensic evidence | Ranger/EA candidate |

The matrix is a scoping aid, not proof of originality.

## Preliminary findings

### EA-C001 — Evidence Object

The broad idea "signed object carrying provenance and verification metadata" is **not novel**. C2PA manifests, in-toto link metadata, SLSA attestations, transparency-log entries, and forensic evidence-management practice establish substantial prior art.

A defensible `EA-C001` contribution, if one survives broader review, must therefore be narrower. Current candidate formulation:

> A domain-general evidence object that binds deterministic identity/integrity material to typed evidentiary claims and verification context, while preserving unsupported assumptions and refusing to promote cryptographic integrity into semantic truth.

This formulation still requires peer-reviewed comparison, a formal minimum-sufficiency argument, and independent evaluation.

### EA-C002 — Evidence Graph

The broad idea "a graph representing provenance" is **not novel**; W3C PROV is direct prior art, and C2PA/in-toto/SLSA each encode related lineage/step relationships.

A defensible `EA-C002` contribution, if one survives broader review, must focus on the semantics and verification state of heterogeneous evidence edges. Current candidate formulation:

> A typed evidence graph in which observation, derivation, inference, authority, decision, command/action, custody, and consequence relationships can be independently evaluated, and where graph connectivity never implies that an unsupported edge is true.

This requires a canonical relation algebra, formal semantics, comparison to provenance-security graph literature, and experiments demonstrating useful distinctions not already captured by existing models.

## Falsification criteria

`EA-C001` should be revised or retired as an original contribution if prior work already provides the same domain-general object semantics, claim-type separation, independent verification model, and explicit unsupported-assumption behavior.

`EA-C002` should be revised or retired if prior work already provides materially equivalent typed evidence-edge semantics and verifier-state propagation across observation/inference/authority/action/consequence relationships.

Finding such work is a successful research result, not a project failure.

## Required next literature expansion

Before either contribution is promoted from `candidate`:

1. run a systematic scholarly search in IEEE Xplore, ACM Digital Library, SpringerLink, Scopus/Web of Science if available, arXiv for discovery only, and Google Scholar for citation chaining;
2. add classic data-provenance/database provenance work and provenance semirings;
3. add secure/tamper-evident audit log research beyond Certificate Transparency;
4. add remote attestation / trusted execution environment literature;
5. add digital chain-of-custody and forensic provenance models;
6. add knowledge/provenance graph verification literature;
7. add AI decision provenance/accountability literature;
8. add cyber-physical/robotics event provenance and safety-assurance cases;
9. record search terms, dates, inclusion/exclusion criteria, and negative searches;
10. obtain external academic review of the resulting nearest-neighbor set.

## Promotion status

- `EA-C001`: remains **candidate**.
- `EA-C002`: remains **candidate**.

This first pass materially narrows both claims but does not establish novelty.