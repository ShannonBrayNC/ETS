# ETS Doctoral Application Dossier — City St George's

**Candidate:** Shannon Bray  
**Research programme:** Evidence Architecture / Evidence Transparency System (ETS)  
**Primary route:** PhD in Computer Science by Prospective Publication  
**Primary research fit:** Software Reliability; dependable and trustworthy systems; formal methods; AI/system assurance; cyber-physical provenance  
**Status:** application/supervisor-contact draft  
**Prepared:** 2026-09-10

## 1. Route decision

City St George's, University of London is the strongest immediate doctoral-home target identified so far for ETS because its Computer Science programme explicitly offers a **PhD by Prospective Publication** alongside the major-thesis and prior-publication routes.

This is materially better aligned to the current ETS state than a PhD by prior/public works route. ETS already has a substantial architecture, implementation, formal-analysis and experimental foundation, but its strongest doctoral claims still require systematic literature qualification, prospective experiment protocols, peer-reviewed publication, external replication and independent scholarly scrutiny. Those are appropriate doctoral activities rather than prerequisites that should be completed before registration.

Current university guidance states that the prospective-publication route:

- uses the same entrance requirements as the major-thesis PhD;
- requires a coherent plan of related projects leading to publications;
- normally includes between three and six research outputs published or submitted during registration;
- does not permit pre-registration publications to be examined as part of the prospective-publication thesis;
- requires the thesis to integrate the outputs into a coherent whole with an overarching hypothesis and sufficient literature/contextual analysis;
- is offered by the Computer Science programme, whose research areas include Software Reliability and Artificial Intelligence/Machine Learning;
- allows consideration, in addition to the normal academic route, of applicants with extensive professional experience in the proposed research area.

Official sources:

- https://www.citystgeorges.ac.uk/prospective-students/courses/research/computer-science
- https://www.citystgeorges.ac.uk/__data/assets/pdf_file/0006/797172/PhD-by-Prospective-Publications-Guidance-July-2025.pdf
- https://www.citystgeorges.ac.uk/research/centres/software-reliability

### Strategic implication

Do **not** wait for ETS to accumulate a completed doctoral dataset or external institutional adoption before approaching supervisors. Use the existing corpus to establish feasibility, research maturity and candidate capability. Reserve the decisive literature qualification, prospective experimental evidence, peer-reviewed publications, independent reproduction and thesis-level synthesis for the registered research programme.

## 2. Working doctoral title

**Independent Verification of Consequential Machine Actions: An Evidence Architecture for Distributed, AI and Cyber-Physical Systems**

Alternative concise title:

**Evidence Architecture for Independently Verifiable Machine Action**

## 3. Proposed overarching research question

**Can a distributed system produce independently verifiable evidence sufficient for an independent verifier to reconstruct and evaluate the provenance, identity, authority, policy context, decision, action and resulting state of a consequential event without requiring trust in the originating system?**

This is the canonical ETS `RQ0` and remains deliberately unanswered.

Supporting questions are maintained in `RESEARCH_QUESTIONS.md` and cover evidence representation, evidence relationships, trust decomposition, offline/asynchronous evidence, AI decision evidence, cyber-physical provenance, adversarial robustness and consequence custody.

## 4. Research problem

Modern digital, AI and autonomous systems increasingly make or execute consequential decisions, yet the evidence available after an event is commonly produced by the same systems whose behavior is under examination. Conventional logs, signed records, audit trails and provenance graphs can establish useful properties, but they do not automatically establish completeness, semantic truth, correct authority, actual execution or resulting physical/digital consequence.

The research problem is therefore not simply how to make logs tamper-evident. It is how to construct and evaluate an evidence architecture in which an independent verifier can distinguish:

- what was observed from what was inferred;
- what was asserted from what was independently checkable;
- identity and integrity from semantic truth;
- authority from capability;
- command issuance from execution;
- intended consequence from independently observed resulting state;
- cryptographic guarantees from external trust assumptions;
- absence of evidence from evidence of absence.

The work investigates whether these distinctions can be represented, preserved and verified across distributed software, AI-mediated action and cyber-physical systems using a common bounded evidentiary model.

## 5. Candidate contribution to knowledge

The research does **not** claim novelty for hashing, digital signatures, Merkle structures, transparency logs, provenance graphs, W3C PROV, event histories, chain-of-custody records, attestation or append-only storage individually. Those are established mechanisms.

The candidate contribution is the formal and empirical investigation of a compositional **Evidence Architecture** that treats evidentiary properties and trust boundaries as separately inspectable claims and carries those claims across the full machine-action chain.

The strongest candidate contributions currently are:

1. **Evidence Object and Evidence Graph semantics** that separate identity, integrity, provenance, custody, authority, verification context, epistemic state and consequence evidence without promoting graph membership or cryptographic integrity into a claim of truth.
2. **Explicit trust/claim-boundary decomposition** so verifier output can preserve useful guarantees while retaining unsupported assumptions and uncertainty.
3. **Machine-action provenance** for AI-assisted or nondeterministic systems that captures externally inspectable inputs, runtime/model identity, policy, declared decision, authority, action and result without claiming access to hidden reasoning.
4. **Cyber-physical provenance and consequence custody** that separates sensor observation, inference, decision, command, actuator behavior and resulting physical state.
5. **Distributed/offline continuity and adversarial qualification** establishing the conditions under which evidentiary properties survive partitions, reordering, asynchronous synchronization, omission, manipulation and bounded component compromise.

All remain candidate contributions until prior art, method, experimental evidence, limitations and independent scrutiny support them. `CONTRIBUTION_LEDGER.md` is the canonical contribution-control record.

## 6. Current preliminary research base

The existing ETS corpus is intended to demonstrate research feasibility rather than complete the doctoral proof. It presently includes:

- canonical research questions and hypotheses (`RESEARCH_QUESTIONS.md`);
- a candidate contribution ledger (`CONTRIBUTION_LEDGER.md`);
- a doctoral experiment ledger (`EXPERIMENT_LEDGER.md`);
- formal Evidence Architecture and evidence-theory material (`docs/dissertation/FORMAL_ARCHITECTURE.md`, `docs/dissertation/EVIDENCE_THEORY.md`);
- first-pass prior-art work for Evidence Objects and Evidence Graphs (`WP1_EVIDENCE_OBJECT_GRAPH_PRIOR_ART.md`);
- implemented Edge/Gateway/Verifier and evidence-processing contracts;
- formal specifications and bounded-model work, including TLA+/Alloy artifacts for selected properties;
- offline/asynchronous transport and reconciliation work;
- AI Witness and Black Box architecture;
- Ranger R0 as a cyber-physical reference research platform;
- reproducibility, simulation, failure and adversarial-test infrastructure.

The presence of these artifacts is preliminary evidence that the proposed research programme is technically executable. Passing implementation tests is not treated as proof that a research hypothesis is true.

## 7. Proposed methodology

The doctorate should use a mixed computer-science methodology combining systematic scholarship, formal methods, experimental systems research and adversarial evaluation.

### Phase A — Literature and novelty qualification

Conduct a systematic literature review and closest-work analysis spanning:

- W3C PROV and provenance models;
- secure/tamper-evident logging and transparency systems;
- digital forensics and chain of custody;
- event sourcing and distributed histories;
- software supply-chain provenance;
- remote attestation and trusted execution environments;
- assurance cases and dependable systems;
- AI accountability/provenance;
- autonomous/cyber-physical assurance;
- formal verification and distributed-systems fault models.

Each candidate contribution will be narrowed, revised or rejected against the literature rather than defended as a product feature.

### Phase B — Formalization

Define the Evidence Object, Evidence Graph, trust-boundary taxonomy, verification vector/state model and consequence-custody model formally enough to establish explicit invariants, assumptions and nonclaims.

Use suitable formal techniques such as state-transition modeling, temporal logic/model checking and relational specification for bounded properties. Formal claims will be kept separate from empirical and operational claims.

### Phase C — Prospective digital/distributed experiments

Create preregistered or otherwise prospectively recorded protocols for:

- canonicalization and cross-implementation identity/integrity;
- evidence reconstruction under asynchronous transport;
- partition, delay, reordering, duplication and later synchronization;
- omission and tampering cases;
- independent-verifier reconstruction;
- disagreement between origin records and independent observations.

### Phase D — AI machine-action experiments

Use AI Witness/reference workloads to evaluate whether an independent verifier can reconstruct externally observable machine-action context without relying on hidden chain-of-thought or unverifiable internal reasoning.

Experimental variables should include model/runtime identity, input/context capture, policy/authority changes, nondeterministic outputs, tool execution, omitted records and independent consequence observation.

### Phase E — Cyber-physical experiments

Use Ranger R0 or an equivalent instrumented cyber-physical platform to evaluate the chain:

`Observation -> Inference -> Decision -> Authority -> Action -> Resulting State`

The experimental design should explicitly separate:

- command evidence;
- actuator-execution evidence;
- independent physical-result evidence;
- sensor trust and uncertainty.

Controlled fault injection should include dropped/altered telemetry, stale sensor information, command rejection, actuator non-execution, delayed observation, contradictory observers and bounded identity/authority faults.

### Phase F — Adversarial qualification and independent reproduction

Evaluate which ETS claims remain sound, degrade detectably or fail under defined attacker capabilities and system faults. Negative results are first-class outputs.

Release reproducible experiment packages and seek independent reproduction by another researcher or laboratory where practical.

## 8. Data and evidence plan

The initial programme does not require a pre-existing external institutional dataset.

The core data can be generated prospectively from controlled research systems and consists primarily of:

- canonical Evidence Objects and graph relationships;
- signed/anchored verification metadata;
- system and observer telemetry;
- policy/authority state;
- AI model/runtime and tool-action records;
- Ranger sensor, command, actuator and resulting-state observations;
- injected-fault ground truth;
- verifier outputs and reconstruction results;
- performance/resource measurements.

External organizational datasets can later strengthen ecological validity but are not required to establish the initial research design. Human-subject and personal-data collection should be avoided unless a later research question requires it and receives the appropriate ethics approval.

## 9. Evaluation criteria

Candidate quantitative and qualitative measures include:

- independent reconstruction completeness;
- correct separation of verified, asserted, contradicted and unknown claims;
- manipulation/fault detection rate within declared trust boundaries;
- false attribution or false-confidence rate;
- provenance continuity through partition/reconciliation;
- verifier agreement across independent implementations;
- ability to distinguish command from observed execution/consequence;
- performance, storage and latency overhead;
- robustness as independent observation channels are removed or compromised;
- reproducibility by a third party.

The research should explicitly report where verification is impossible from available evidence.

## 10. Prospective-publication thesis plan

The working publication sequence is intentionally aligned to a prospective-publication doctorate. Final count and venues should be set with supervisors and discipline expectations.

### Paper 1 — Evidence Architecture foundations

Formal problem definition, trust decomposition, evidence/nonclaim semantics and the relationship to existing provenance, forensic and assurance approaches.

### Paper 2 — Evidence Objects and Evidence Graphs

Minimum-sufficiency investigation, typed evidentiary relationships, contradiction/uncertainty treatment and comparison with W3C PROV and adjacent models.

### Paper 3 — Independent verification in distributed/offline systems

Formal and experimental evaluation of asynchronous transport, partition, reconciliation, omission and verifier reconstruction.

### Paper 4 — Evidence for AI-mediated machine action

Evaluation of externally inspectable AI action evidence without dependency on hidden reasoning traces.

### Paper 5 — Cyber-physical provenance and consequence custody

Ranger-based experiments distinguishing observation, decision, authority, command, actuator execution and independently observed resulting state.

### Paper 6 — Adversarial qualification and evidence-of-evidence

Fault/attacker model, negative results, boundary failures, reproducibility and evidence generated about the qualification process itself.

A thesis commentary/synthesis would establish the overarching hypothesis, integrate results, provide literature context and explain which candidate contributions survived scrutiny.

## 11. What remains doctoral work

The following should **not** be treated as admission blockers unless a specific university requires them:

- final systematic literature review;
- final novelty determination;
- completed prospective datasets;
- all Ranger physical experiments;
- AI nondeterministic replication studies;
- full adversarial campaign;
- external reproduction;
- peer-reviewed prospective publications;
- final statistical analysis;
- final supported/refuted contribution set;
- thesis synthesis.

These are principal outputs of the proposed doctorate.

## 12. Immediate supervisor targets

### Primary — Professor Ilir Gashi

Director, Centre for Software Reliability. His current role and research environment align strongly with software reliability, security, dependability and empirical assessment.

Profile: https://www.citystgeorges.ac.uk/about/people/academics/ilir-gashi

### Strong co-supervision/alternate fit — Professor Robin Bloomfield

Research interests include software/system dependability, safety and assurance cases, security-informed safety, critical infrastructure and trustworthiness of software-based systems.

Profile: https://www.citystgeorges.ac.uk/about/people/academics/robin-bloomfield

### Strong co-supervision/alternate fit — Professor Peter Bishop

Research includes software/system dependability, system safety and security, assurance-case methodology and assurance strategies for autonomous vehicles.

Profile: https://www.citystgeorges.ac.uk/about/people/academics/peter-bishop

## 13. Initial supervisor outreach draft

**Subject:** Prospective PhD research — independently verifiable evidence for AI and cyber-physical systems

Professor Gashi,

I am preparing a Computer Science PhD proposal around a research programme I have been developing on independently verifiable evidence for consequential machine actions.

The central question is whether a distributed system can produce sufficient evidence for an independent verifier to reconstruct and evaluate the provenance, identity, authority, policy context, decision, action and resulting state of an event without requiring trust in the originating system.

I have already developed a substantial preliminary research platform, Evidence Architecture / ETS, including formal models, implementation and verifier work, distributed/offline evidence experiments, AI-action provenance work, and a cyber-physical reference platform called Ranger. I am deliberately not treating those implementations as proof of the research claims. The remaining work includes systematic literature and novelty qualification, prospective experimental protocols, formal refinement, adversarial testing, independent reproduction and peer-reviewed publication.

City St George's PhD by Prospective Publication route appears particularly well matched because I want the decisive experiments and publications to occur under doctoral supervision rather than attempting to present the existing engineering corpus as a completed PhD.

The Centre for Software Reliability's work on rigorous dependability assessment, security, formal methods and assurance is especially close to the methodological direction I believe this research requires.

Would you be willing to assess whether this topic could fit the Centre and whether you, or another member of the group, might be appropriate to discuss potential supervision with? I can provide a concise research prospectus, the canonical research questions/contribution ledger and links to the public research repository.

Regards,
Shannon Bray

## 14. Questions to resolve with City St George's before formal application

These are admissions/supervisory questions, not research prerequisites:

1. Confirm that the Department of Computer Science will accept this project specifically under the PhD by Prospective Publication route for the intended intake.
2. Confirm whether the candidate's professional/research record is sufficient under the programme's provision for applicants with extensive professional experience, based on the candidate's exact academic transcript/degree history.
3. Establish the supervisory team and whether the Centre for Software Reliability is the appropriate home.
4. Confirm the publication expectations for Computer Science: expected number/type of outputs, venue standards, first-authorship expectations and handling of collaborative papers.
5. Confirm the next viable application/start window because the published 2026 Computer Science deadlines have passed for the October 2026 start.
6. Confirm residence/attendance requirements and whether part-time or remote-compatible study is feasible for a US-based candidate.

## 15. Application dossier still to build

The next application artifacts should be produced from this prospectus and the existing research corpus:

- research-focused academic CV;
- 1,000–2,000 word university-neutral research proposal;
- 1–2 page contribution summary;
- selected public research/engineering portfolio with immutable links;
- qualification/transcript inventory;
- professional/research achievements relevant to exceptional-entry consideration;
- referee strategy;
- literature map and bibliography sufficient to demonstrate current field awareness;
- route-specific application wrapper for City St George's.

## 16. Decision rule

Supervisor contact can begin now.

Formal submission should follow once the qualification/entry route, supervisory fit and next intake are confirmed and the academic CV plus concise proposal are complete.

Do not delay supervisor contact for completed empirical data, external commercial adoption, Ranger hardware completion, peer-reviewed ETS publications or institutional buy-in. Those items may strengthen the case later, but for the prospective-publication route the decisive research should remain prospective and academically supervised.
