# NSF SBIR/STTR Phase I Research Dossier — ETS

Status: Working research plan; do not submit as a Project Pitch without technical-novelty review
Date: 2026-09-03
Program baseline: NSF 26-510

## 1. Purpose

This dossier converts ETS from a product/platform description into a falsifiable Phase I research program. It responds directly to NSF Project Pitch feedback that the prior submission did not sufficiently articulate a new, high-risk technological innovation or the R&D required to overcome key technical challenges.

The next Project Pitch must lead with the unproven technical capability, not with ETS product features, connectors, cloud deployment, or market benefits.

## 2. Candidate core technological innovation

Working name: **Trust-Independent Evidence State (TIES)**

Working hypothesis:

> A distributed evidence object can preserve independently verifiable provenance, integrity, identity, custody, temporal ordering, policy state, and transformation history while crossing heterogeneous and mutually distrustful systems, including intermittently connected or compromised participants, without requiring continued trust in the originating platform or Lantern Protocol infrastructure.

This hypothesis is intentionally falsifiable. Phase I must determine the conditions under which it succeeds, fails, or becomes indeterminate.

## 3. Research distinction

Phase I is **not** proposed as funding to build or incrementally improve:

- an M365 connector;
- a mobile application;
- ETS Edge, Gateway, Verifier, AI Witness, Vault, or Black Box as commercial features;
- ordinary cloud deployment or integration;
- a generic blockchain/provenance application;
- routine cryptographic signing or hashing;
- product testing, marketing, manufacturing, or business development.

Existing ETS components should instead serve as experimental apparatus and heterogeneous evidence producers/consumers for testing the underlying research hypothesis.

## 4. Formal research direction

A preliminary evidence state may be represented conceptually as:

`E_t = f(O, I, P, C, T, W, X)`

where candidate dimensions include:

- `O`: evidence object / object identity;
- `I`: integrity and cryptographic assertions;
- `P`: provenance assertions;
- `C`: custody events and relationships;
- `T`: temporal information and causal ordering;
- `W`: witness/attestation relationships;
- `X`: transformations and derived-object relationships.

A verifier should evaluate an evidence package and proof material without trusting the producer:

`V(E, Π) -> {VALID, INVALID, INDETERMINATE}`

The INDETERMINATE state is a first-class research requirement. ETS must not claim cryptographic certainty where evidence is missing, contradictory, unverifiable, or outside the guarantees of the model.

## 5. Candidate Phase I technical objectives

### Objective 1 — Formalize trust-independent evidence state

Research a machine-verifiable representation for evidence identity, provenance, integrity, custody, temporal state, policy assertions, witnesses, and transformations across administrative domains.

Key challenges:

- canonicalization across heterogeneous sources;
- causal versus wall-clock ordering;
- identity/key lifecycle changes;
- conflicting assertions;
- selective disclosure and privacy boundaries;
- derived/transformed evidence relationships;
- avoiding dependence on a single central authority.

Falsification question: Can independent implementations derive materially different validity conclusions from the same admissible evidence-event set?

### Objective 2 — Offline and partitioned evidence reconciliation

Research deterministic reconciliation when evidence producers operate offline or across network partitions.

Adversarial conditions should include:

- clock drift;
- out-of-order events;
- duplicated events;
- missing events;
- delayed synchronization;
- conflicting custody histories;
- malicious reordering;
- replay of otherwise valid assertions.

Falsification question: Are there ambiguity classes in which the protocol cannot distinguish a legitimate partition/reconciliation from malicious history manipulation? If so, characterize them and require INDETERMINATE rather than false validity.

### Objective 3 — Compromised/hostile participant resistance

Determine what can and cannot be detected when one or more evidence participants become hostile or compromised.

Experimental attacks should include:

- metadata modification;
- backdating;
- deletion of intermediate custody events;
- identity/key cloning or misuse where experimentally appropriate;
- replay;
- contradictory witnesses;
- substitution of evidence objects;
- tampering with transformation history.

Falsification question: Under which trust and compromise assumptions can a malicious participant construct a package accepted as VALID despite a material evidence-history violation?

### Objective 4 — Producer-independent verification

Develop and test an independent verifier that requires no Lantern API, Lantern database, Lantern cloud account, or cooperation from the evidence producer after package creation.

Falsification question: Which verification claims cannot be reproduced from the portable evidence package plus explicitly identified external trust anchors?

## 6. Required experimental methodology

Before Pitch #2, define:

1. threat and trust assumptions;
2. baseline technologies and comparison methods;
3. adversarial test corpus;
4. reproducible experimental harness;
5. quantitative success/failure thresholds;
6. false-acceptance and false-rejection measurements;
7. deterministic reconciliation measurements;
8. computational/storage overhead measurements;
9. independent-verifier interoperability test;
10. explicit failure and indeterminate criteria.

Do not invent favorable metrics merely for the application. Establish defensible thresholds from literature review, prototype measurements, customer requirements, or experimental feasibility.

## 7. State-of-the-art / novelty work required

Before claiming novelty, complete a documented comparison against relevant technical classes, including at minimum:

- digital signatures and PKI;
- cryptographic timestamping;
- append-only/Merkle transparency logs;
- content-addressed storage;
- distributed ledgers/blockchains where relevant;
- software supply-chain attestations/provenance frameworks;
- C2PA/content provenance approaches;
- digital evidence chain-of-custody systems;
- secure/auditable logging;
- distributed event ordering and conflict-resolution methods;
- trusted execution/hardware-rooted attestation where relevant.

For every class, document:

- what problem it solves;
- its trust assumptions;
- what ETS/TIES would reuse rather than claim as novel;
- the unresolved technical gap;
- why combining existing components is insufficient;
- what Phase I research must prove.

No novelty statement should survive into the Project Pitch unless this comparison supports it.

## 8. Proposed Phase I research artifacts

A successful research phase should produce evidence beyond a product demo:

- formal evidence-state specification;
- protocol/state-transition specification;
- threat/trust model;
- reconciliation algorithm and analysis;
- portable evidence package/profile;
- independent reference verifier;
- adversarial corpus and test harness;
- experimental results with failure cases;
- interoperability results across heterogeneous producers;
- performance/overhead characterization;
- documented limitations and indeterminate cases.

## 9. Existing ETS components as experimental apparatus

Existing work can reduce implementation overhead without becoming the proposed innovation:

- ETS Edge — experimental edge evidence producer;
- Provenance / ETS-Mobile — mobile evidence producer;
- Microsoft 365 connector — third-party administrative-domain producer/consumer;
- ETS Gateway — transport/interchange apparatus;
- ETS Verifier — candidate verification implementation;
- AI Witness — machine-generated assertion/witness source;
- ETS Black Box — recovery/adversarial evidence environment.

The Phase I claim must remain valid even if these product surfaces change.

## 10. NSF Project Pitch #2 structure

### Technology Innovation — up to current NSF form limit

Must explain:

- the precise unproven technical innovation;
- its origin;
- current technical gap;
- why existing approaches do not solve it;
- why the work is high-risk/high-impact R&D;
- what new capability becomes possible if successful.

### Technical Objectives and Challenges — up to current NSF form limit

Must explain:

- specific research objectives;
- scientific/engineering uncertainty in each;
- experiments/methods;
- technical failure modes;
- how Phase I materially reduces technical risk;
- measurable feasibility criteria.

### Market Opportunity

Map the research result to customers that require evidence to remain verifiable across trust boundaries, potentially including regulated enterprise, cybersecurity, compliance/audit, government, legal/eDiscovery, critical infrastructure, AI accountability, and physical/mobile evidence workflows. Competitive claims must be evidence-backed.

### Company and Team

Explain technical capability to execute the R&D and identify real gaps. Do not hide missing expertise. Determine whether the research requires additional cryptography, distributed-systems, formal-methods, digital-forensics, statistics, or academic expertise and document a credible plan to fill those gaps.

## 11. Submission constraints / governance

- Treat the next pitch as a scarce submission opportunity.
- Do not resubmit a lightly edited version of Pitch #1.
- Archive the rejection and the exact prior pitch for a sentence-by-sentence gap analysis.
- Validate all application limits and requirements against the solicitation/form in force on the submission date.
- Separate factual prior art from marketing claims.
- Separate demonstrated ETS capability from proposed/unproven research.
- Never describe an existing implementation as unproven merely to manufacture technical risk.
- Record negative experimental results; they are relevant to defining the technology's actual guarantees.

## 12. Immediate next-step gate

**Gate NSF-R0: Technical Novelty & Falsifiability Review**

Do not draft Pitch #2 as final application copy until R0 passes.

R0 requires:

1. recover and archive the exact rejected Project Pitch;
2. map every reviewer criticism to the relevant submitted sentence/omission;
3. complete the state-of-the-art comparison;
4. reduce the candidate innovation to one primary technical claim;
5. define trust/threat assumptions;
6. define 3–4 falsifiable technical objectives;
7. define experimental methods and initial metrics;
8. identify technical/team gaps;
9. produce a one-page research hypothesis brief;
10. conduct a red-team review asking: **Is this genuinely new R&D, or sophisticated systems integration?**

Only after R0 passes should the team draft the next NSF Project Pitch.

## 13. Decision record

Current candidate thesis: **Trust-Independent Evidence State across heterogeneous and partially trusted systems.**

This is a candidate research thesis, not yet a validated novelty claim. The immediate work is to attempt to disprove its novelty and feasibility assumptions before committing the next NSF submission opportunity.
