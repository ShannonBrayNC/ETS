# ETS Dissertation Publication Requirements

Status: active program specification  
Program issue: `#120`  
System: Evidence Transparency System (ETS)  
Operating mode: dissertation-only priority  
Normative terms: **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are requirements.

## 1. Purpose

This specification converts the ETS research foundation into a bounded,
dependency-aware program for producing an advisor-ready, committee-ready, and
institutionally compliant dissertation. It is the human-readable source for the
machine-readable queue in `config/dissertation-work-queue.json`.

The program MUST distinguish four release states:

1. research prospectus;
2. public technical report or preprint;
3. committee-facing dissertation draft;
4. final institutionally accepted dissertation.

Completion of a repository task MUST NOT be represented as advisor approval,
committee approval, degree conferral, patent clearance, legal review, peer-review
acceptance, or institutional deposit.

## 2. Program Controls

### 2.1 Single-program focus

- Dissertation work is the only enabled autonomous ETS work program.
- Each hourly pass MUST select at most one bounded queue item.
- A pass MUST NOT bypass a dependency, human gate, evidence gate, or approval gate.
- Unrelated feature work MUST remain paused unless it is necessary to satisfy a
  dissertation requirement and is explicitly linked from the selected queue item.
- Pull-request validation remains permitted because it supplies dissertation evidence.

### 2.2 Source of truth

The following order resolves conflicts:

1. explicit advisor, committee, Graduate Education, IP, or legal decision;
2. `config/dissertation-work-queue.json`;
3. this requirements specification;
4. claim traceability and formal evidence manifests;
5. chapter plans, research notes, and historical sprint documents.

Historical documents MUST be corrected when they conflict with newer executed
evidence. A later narrative date alone does not prove correctness; exact commit,
tool, command, result, and retained artifact data control technical claims.

### 2.3 Hourly chunk contract

Every automation-eligible item MUST include:

- a stable task identifier;
- sprint and priority;
- dependencies;
- bounded objective;
- required outputs;
- acceptance criteria;
- validation commands or review procedure;
- claim-risk classification;
- automation eligibility;
- human-approval requirements;
- status and completion evidence.

An hourly pass MUST:

1. read the queue from the default branch;
2. inspect open ETS dissertation issues and pull requests;
3. perform an anti-duplication check;
4. select the first ready item using the deterministic selection policy;
5. implement only that item;
6. validate the result proportionately;
7. update the queue item and its completion evidence;
8. update or open the linked issue and pull request;
9. stop without selecting a second item.

## 3. Global Scientific Requirements

### 3.1 Claim discipline

Every material claim MUST be classified as one of:

- implemented;
- empirically observed;
- bounded model;
- fairness-scoped;
- statistically supported;
- process model;
- pending;
- not claimed.

Every material claim MUST map to one or more authoritative sources or repository
artifacts. ETS MUST NOT claim semantic truth, perfect completeness, universal
Byzantine consensus, universal asynchronous liveness, Internet-scale adversarial
correctness, production throughput, legal sufficiency, election correctness, or
AI fairness/explanation correctness without separate evidence and approval.

### 3.2 Evidence integrity

Executed evidence MUST record:

- repository and exact commit SHA;
- clean/dirty state or workflow head SHA;
- operating system and architecture;
- runtime and tool versions;
- command or workflow identifier;
- model bounds, seed, dataset, and configuration;
- start/end timestamps;
- pass, fail, timeout, skipped, or blocked result;
- durable artifact location and checksum;
- limitations and excluded properties.

Missing, expired, failed, timed-out, or inaccessible evidence MUST NOT be cited as
passing evidence.

### 3.3 Citation integrity

References MUST use a normalized bibliographic source. Each reference MUST include
enough metadata to resolve the work, preferably DOI, RFC, standard number, or stable
publisher URL. The program MUST distinguish primary, peer-reviewed, standard,
government, official documentation, preprint, and secondary sources.

Source review MUST record relevance, support strength, limitations, and any conflict
of interest. Automated work MUST NOT fabricate a citation or infer bibliographic
metadata that was not verified.

### 3.4 Research ethics, privacy, and security

- Experiments MUST use synthetic or explicitly approved non-sensitive data.
- Real customer, voter, patient, legal-case, personnel, or unpublished research data
  MUST NOT be committed.
- Human-subjects, export-control, controlled-data, and IRB applicability MUST be
  decided by the institution or authorized reviewer rather than automation.
- Secrets, private keys, tokens, raw evidence payloads, and confidential IP analysis
  MUST NOT be placed in public artifacts.

## 4. Sprint Requirements

## Sprint D0 — Academic Governance and Publication Control

Objective: establish the human and institutional authority for the dissertation.

Requirements:

- D0-R1: An advisor MUST confirm or revise ETS as a viable dissertation topic.
- D0-R2: The program/restart status, catalog year, degree requirements, residency,
  enrollment, comprehensive examination, and administrative path MUST be recorded.
- D0-R3: The dissertation committee path and required membership MUST be confirmed.
- D0-R4: The working thesis, research questions, contribution boundaries, and first
  chapter/paper target MUST receive an explicit decision.
- D0-R5: Authorship, acknowledgment, contributor, AI-assistance disclosure, research
  ethics, copyright, IP, patent, embargo, and public-disclosure decisions MUST be
  recorded before external publication.

Acceptance gate: advisor and institutional decisions are recorded with decision
date, decision maker/role, scope, and follow-up requirements. Automation MAY prepare
decision packets but MUST NOT mark a human decision complete.

## Sprint D1 — Evidence Baseline and Formal-Status Reconciliation

Objective: create one auditable technical baseline for all dissertation claims.

Requirements:

- D1-R1: Freeze a dissertation evidence candidate SHA and environment manifest.
- D1-R2: Reconcile `EVIDENCE_CAPTURE_REPORT.md`, formal-status snapshots, proof index,
  theorem registry, traceability matrices, issue state, and current workflow results.
- D1-R3: Complete or accurately bound issue `#70` full TLC evidence capture.
- D1-R4: Remediate Lean and Apalache failures or record them as failed/pending with
  exact logs and impact on claims.
- D1-R5: Retain formal, benchmark, replay, test, lint, type, dependency, and secret-scan
  artifacts outside expiring workflow-only storage when policy permits.
- D1-R6: Update the machine-readable claim traceability manifest so no claim cites
  stale, missing, or contradictory evidence.
- D1-R7: Review and disposition dissertation-relevant open pull requests, stale
  branches, duplicate artifacts, and issue state before freezing manuscript inputs.

Acceptance gate: one evidence ledger identifies the authoritative result for every
claimed property and passes automated cross-reference validation.

## Sprint D2 — Manuscript and Citation Infrastructure

Objective: create a buildable dissertation source rather than a collection of notes.

Requirements:

- D2-R1: Create a master manuscript and one source file per approved chapter.
- D2-R2: Create title-page, abstract, acknowledgments, contents, figure/table lists,
  references, appendices, and vita placeholders in institution-required order.
- D2-R3: Establish a normalized BibTeX or advisor-approved equivalent bibliography.
- D2-R4: Establish citation keys, glossary, acronyms, notation, definition, theorem,
  figure, table, and cross-reference conventions.
- D2-R5: Implement a reproducible manuscript build and lint path with no broken
  references, duplicate keys, or missing required sections.
- D2-R6: Record word/page targets as planning controls, not artificial completion
  metrics.

Acceptance gate: a clean checkout can produce a reviewable manuscript artifact with
all structural sections present and clearly marked draft content.

## Sprint D3 — Literature Review, Related Work, and Novelty

Objective: demonstrate command of prior work and bound the original contribution.

Requirements:

- D3-R1: Define a documented literature search and inclusion/exclusion protocol.
- D3-R2: Cover transparency logs, authenticated data structures, append-only systems,
  provenance, chain of custody, digital evidence, event sourcing, audit systems,
  formal methods, BFT/consensus, observability/SIEM, computational trust, epistemic
  logic, AI governance, and reproducible systems research.
- D3-R3: Prioritize peer-reviewed primary research, standards, RFCs, government
  publications, and official technical specifications.
- D3-R4: Build a related-work matrix comparing assumptions, guarantees, evidence
  boundaries, threat model, verification model, and limitations.
- D3-R5: State novelty as bounded synthesis, extension, formalization, artifact, or
  empirical contribution; avoid invention-from-nothing language.
- D3-R6: Reconcile dissertation novelty with the prior-art and IP review without
  publishing confidential counsel material.

Acceptance gate: every novelty statement is supported by related-work analysis and
has a counterargument/limitation review.

## Sprint D4 — Theory, Protocol, Threat Model, and Formal Verification

Objective: make the intellectual and formal core internally consistent.

Requirements:

- D4-R1: Define evidence, observation, visibility, integrity, trust, confidence,
  certainty, disagreement, omission suspicion, freshness, replay, and degradation.
- D4-R2: State research questions, system model, adversary model, trust assumptions,
  cryptographic assumptions, failure model, network model, and out-of-scope threats.
- D4-R3: Specify the ETS layer model and protocol semantics with normative language.
- D4-R4: Give every theorem/invariant a statement, assumptions, status, validation
  method, result, implementation relation, and limitation.
- D4-R5: Complete or explicitly defer refinement mappings between formal state and
  Python implementation state.
- D4-R6: Resolve terminology and status disagreements among formal documents.
- D4-R7: Clearly distinguish model checking, symbolic analysis, proof sketches,
  mechanized proofs, tests, and universal theorem proof.

Acceptance gate: the formal coverage table is consistent with retained outputs and
contains no status that cannot be reproduced or independently reviewed.

## Sprint D5 — Methodology, Evaluation, and Reproducibility

Objective: produce a defensible evaluation rather than product demonstrations.

Requirements:

- D5-R1: Select and justify the research methodology, including the role of design
  science, formal analysis, controlled experiment, and artifact evaluation.
- D5-R2: Define research questions/hypotheses, independent/dependent variables,
  controls, baselines, datasets, seeds, repetitions, metrics, and stopping rules.
- D5-R3: Select defensible comparison baselines and explain non-comparable systems.
- D5-R4: Measure functional correctness, proof generation/verification, scaling,
  replay, omission suspicion, conflict visibility, and failure behavior only where
  the implementation and research question support the measurement.
- D5-R5: Report distributions, uncertainty, effect sizes, or justified descriptive
  statistics; do not rely solely on a single machine-dependent timing result.
- D5-R6: Document internal, external, construct, conclusion, and reproducibility
  threats to validity.
- D5-R7: Produce a durable artifact package with manifest, checksums, commands,
  environment, data-generation procedure, raw results, derived results, and license.

Acceptance gate: an independent reviewer can regenerate the bounded results or can
identify an explicit, documented blocker without relying on private data.

## Sprint D6 — Integrated Manuscript, Figures, Tables, and Technical Edit

Objective: convert validated artifacts into one coherent scholarly argument.

Requirements:

- D6-R1: Produce continuous prose for Chapters 1 through 10 in the approved sequence.
- D6-R2: Integrate at least the planned layered architecture, evidence lifecycle,
  verifier disagreement, evidence capture, and claim-boundary figures.
- D6-R3: Integrate contribution, related-work, formal-coverage, implementation,
  evidence-capture, and non-claim tables.
- D6-R4: Ensure every research question is answered and every contribution is
  supported, evaluated, limited, and reflected in the conclusion.
- D6-R5: Perform technical, academic, citation, terminology, accessibility, and
  overclaim edits. Remove promotional language and unsupported comparison cells.
- D6-R6: Run claim-to-evidence, reference, figure/table, acronym, glossary, theorem,
  appendix, and cross-reference audits.
- D6-R7: Produce a complete abstract and defense-ready contribution summary.

Acceptance gate: the manuscript reads as a dissertation rather than a product manual,
protocol brochure, sprint ledger, or concatenation of research notes.

## Sprint D7 — Review, Institutional Formatting, Defense, and Deposit

Objective: pass human, institutional, and archival gates.

Requirements:

- D7-R1: Complete advisor review and all required revision rounds.
- D7-R2: Complete committee-facing circulation and external technical/academic review.
- D7-R3: Apply the current Missouri S&T Word or LaTeX template and specifications.
- D7-R4: Complete early, pre-defense, post-defense, and final format reviews as
  required by Graduate Education.
- D7-R5: Complete defense notice, defense, result/approval forms, and committee edits.
- D7-R6: Complete originality, academic-integrity, accessibility, copyright,
  third-party material, AI-use disclosure, IP/patent, license, and embargo reviews.
- D7-R7: Deposit the approved artifact and archive the reproducibility package using
  stable identifiers where permitted.
- D7-R8: Tag and publish repository materials only after the public-release and IP
  gates pass.

Acceptance gate: institutional acceptance and deposit are confirmed. Repository
automation MUST NOT infer this result from document completeness.

## 5. Deterministic Queue Selection

The selector MUST consider only tasks that are:

- `status = ready`;
- `automation_eligible = true`;
- not marked `approval_required` for the proposed action;
- free of incomplete dependencies;
- free of an active lease or overlapping pull request;
- within the active sprint or a permitted non-blocking preparation lane.

Selection order is:

1. lowest numeric priority;
2. lowest sprint order;
3. lowest task order;
4. lexical task ID as a stable tie breaker.

If no task is ready, the pass MUST report the blocking task and required human or
technical action. It MUST NOT invent substitute work.

## 6. Definition of Done

The program is done only when:

- all automation-eligible tasks are completed with evidence;
- all human gates are explicitly approved;
- the evidence ledger and claim manifest are consistent;
- the dissertation is complete, buildable, cited, illustrated, evaluated, and edited;
- the artifact package is reproducible and durably archived;
- advisor, committee, Graduate Education, defense, IP, copyright, and deposit gates
  are recorded as complete;
- final release text contains no unsupported claim or concealed failed evidence.

Until then, ETS MAY be described as an active dissertation research program or
bounded technical research artifact, but not as an accepted dissertation.

## 7. Institutional Authority References

The D0 and D7 human gates MUST reverify the current institutional rules rather than
assuming this specification remains current. Initial authority references are:

- Missouri S&T Ph.D. Roadmap:
  `https://grad.mst.edu/studentservices/navigatingyourdegreeprogram/requirementsandmilestones/phd/`
- Missouri S&T Thesis and Dissertation Guide:
  `https://grad.mst.edu/studentservices/thesisdissertationguide/`
- Missouri S&T document-submission and format-review process:
  `https://grad.mst.edu/studentservices/thesisdissertationguide/submittingyourdocument/`
- Missouri S&T graduation deadlines and checklist:
  `https://grad.mst.edu/studentservices/navigatingyourdegreeprogram/graduation/`

Repository text is a planning control and MUST NOT supersede an advisor, committee,
department, Graduate Education, research-compliance, or authorized IP decision.
