# ETS Doctoral Application Dossier — City St George's

**Candidate:** Shannon Bray  
**Research programme:** Evidence Architecture / Evidence Transparency System (ETS)  
**Primary route:** PhD in Computer Science by Prospective Publication  
**Primary research fit:** Software Reliability; dependable/trustworthy systems; formal methods; AI/system assurance; cyber-physical evidence  
**Status:** supervisor-contact/application-development draft  
**Originally prepared:** 2026-09-10  
**Updated:** 2026-09-12

## 1. Route decision

City St George's, University of London remains the strongest immediate doctoral-home target identified for ETS because its Computer Science programme explicitly offers a **PhD by Prospective Publication** alongside major-thesis and prior-publication routes.

This route is especially well aligned to the current research state. ETS already provides a substantial preliminary architecture, implementation, formal-analysis and experimental platform, but the decisive scholarly contributions remain prospective: literature qualification, formal refinement, preregistered experiments, peer-reviewed publications, independent challenge and final synthesis.

That is preferable to treating the existing engineering corpus as if the doctorate were already complete.

Current public guidance indicates that the prospective-publication route uses the same entrance requirements as the major-thesis PhD, expects a coherent series of related projects leading to publications produced during registration, and culminates in a thesis integrating those outputs into an overarching scholarly argument.

Official sources to revalidate before formal submission:

- https://www.citystgeorges.ac.uk/prospective-students/courses/research/computer-science
- https://www.citystgeorges.ac.uk/__data/assets/pdf_file/0006/797172/PhD-by-Prospective-Publications-Guidance-July-2025.pdf
- https://www.citystgeorges.ac.uk/research/centres/software-reliability

## 2. Current working title

**Bounded Evidence for Consequential Machine Actions: Formal Non-Collapse Semantics and Consequence Custody Across Distributed, AI and Cyber-Physical Systems**

Continuity title retained for broader framing:

**Independent Verification of Consequential Machine Actions: An Evidence Architecture for Distributed, AI and Cyber-Physical Systems**

## 3. Research questions

### Canonical overarching question — RQ0

**Can a distributed system produce independently verifiable evidence sufficient for an independent verifier to reconstruct and evaluate the provenance, identity, authority, policy context, decision, action and resulting state of a consequential event without requiring trust in the originating system?**

### Narrowed doctoral question

**Does a formal, substrate-independent non-collapse semantics reduce unsupported evidentiary conclusions while preserving supported conclusions across distributed, AI-mediated and cyber-physical machine-action scenarios, and what additional evidence is required to support bounded consequence attribution?**

The supporting RQ1–RQ8 remain canonical in `RESEARCH_QUESTIONS.md`.

## 4. Why the thesis has narrowed

The preliminary research has already produced a useful negative result: existing provenance and attestation systems can express more of the Evidence Architecture surface than a weak comparator would suggest.

W3C PROV already provides rich provenance modeling and qualified relations. RFC 9334 RATS already provides Evidence, Attesters, Verifiers, appraisal policy, Attestation Results, Relying Parties, freshness and explicit trust assumptions. Rich profiles can add domain-specific claims, event time, policy versions, source dependence, uncertainty, authority, action and outcome information. Current 2026 RATS work further explores behavioral evidence, application-layer action/authority/outcome composition and attested inference receipts.

For EXP-002, the internal red-team deliberately constructed the strongest reasonable RATS baseline. Its provisional adverse finding was that all twenty frozen scenarios could be represented through direct RATS semantics or an ordinary rich application profile; no scenario was internally classified `NOT_EQUIVALENT`, and no mandatory R+ extra rule was identified.

That is **not** an independent or confirmatory result. An independent RATS/attestation challenge has been requested from Ned Smith. However, the internal result and emerging prior art are already sufficient to narrow the doctoral contribution away from claims that an evidence envelope, verifier role, graph, rich claim model or attested action/outcome receipt is itself original.

This is a methodological strength of the proposed doctorate: the engineering platform has already exposed a smaller and more falsifiable scientific question.

## 5. Revised candidate contribution to knowledge

The current highest-value candidate contribution is a formal and empirical **non-collapse semantics** for consequential machine-action evidence.

The proposed semantics keeps independently supported propositions separate and prevents unsupported promotion across boundaries such as:

- integrity -> semantic truth;
- identity -> authority;
- current authority -> historical standing;
- evidence freshness -> policy/reference freshness;
- request -> execution;
- execution -> result observation;
- result observation -> causal consequence;
- agreement -> independent corroboration;
- missing evidence -> event absence;
- unknown/unavailable/contradicted -> unsupported positive or negative fact;
- source-evidence validity -> verifier trust;
- provenance/temporal sequence -> causal proof.

A second tightly related candidate is **consequence custody**: the evidence/provenance discipline required to keep requested action, execution evidence, resulting-state observation and bounded consequence attribution separate until the required premises are actually present.

The contribution is intentionally framed as substrate-independent. If the same rules can be implemented through a strong RATS+ profile with materially equivalent results, the correct interpretation is that the semantic rule set—not an ETS-specific container—is the research contribution.

`CONTRIBUTION_LEDGER.md` is the canonical contribution-control record and must remain authoritative over application marketing language.

## 6. Current preliminary research base

The existing ETS corpus demonstrates feasibility and research maturity. It includes:

- canonical RQ0–RQ8;
- a contribution ledger that records narrowed and adverse findings;
- a doctoral experiment ledger;
- formal Evidence Architecture and evidence-theory material;
- W3C PROV relation mapping and closest-work analysis;
- RATS equivalence preregistration and a 20-scenario frozen corpus;
- strongest-RATS internal red-team and external reviewer package;
- 2026 emerging RATS/action-evidence prior-art qualification;
- prospectively registered EXP-001, EXP-002 and EXP-003;
- implemented Edge/Gateway/Verifier evidence-processing contracts;
- TLA+/Alloy/formal artifacts for selected bounded properties;
- offline/asynchronous transport and reconciliation research;
- AI Witness and Black Box architecture;
- Ranger R0 and VRX as cyber-physical research platforms;
- reproducibility, simulation, failure and adversarial-test infrastructure.

Passing implementation tests is not treated as proof of a doctoral hypothesis.

## 7. Proposed methodology

The doctorate should combine systematic scholarship, formal methods, machine-checkable experiments, systems research and adversarial evaluation.

### Phase A — Literature and novelty qualification

Continue structured closest-work analysis across:

- W3C PROV and provenance;
- secure/tamper-evident logs and transparency systems;
- digital forensics and chain of custody;
- supply-chain provenance;
- RATS, attestation and TEEs;
- behavioral evidence and AI inference/action receipts;
- dependable systems and assurance cases;
- autonomous/cyber-physical assurance;
- causal/consequence evidence;
- distributed-systems fault models.

Claims that collapse into established practice must be narrowed or retired.

### Phase B — Formal non-collapse semantics

Define proposition types, epistemic states, positive inference rules, prohibited cross-dimensional promotions, contradiction/defeater semantics, source independence and machine-checkable support traces.

The rule system must be capable of implementation outside the ETS object model.

### Phase C — EXP-003 machine-checkable falsification

EXP-003 is the highest-priority executable doctoral experiment because it directly tests the narrowed thesis without human-subject dependency.

Identical atomic facts will be evaluated under:

1. a rich profile without the frozen mandatory non-collapse calculus;
2. the formal non-collapse calculus;
3. a RATS+ implementation of the same rules.

Primary outcomes include unsupported semantic-promotion rate and supported-conclusion recall. The study will also measure historical-standing error, command/execution/result/consequence collapse, source-independence collapse and epistemic-state collapse.

A RATS+ result equal to the Evidence Architecture implementation is an expected and academically useful outcome because it supports substrate independence while narrowing ETS-specific novelty.

### Phase D — EXP-001 evaluator study

The preregistered human evaluator comparison remains important for determining whether formal semantics improve practical reconstruction behavior. It must proceed only after institutional ethics/IRB determination and packet-equivalence review.

### Phase E — Distributed and AI experiments

Convert asynchronous/offline implementation work into publication-grade experiments and use AI Witness/reference workloads to compare self-reported machine action with independently observable external effect. Hidden chain-of-thought is not required or treated as evidence.

### Phase F — Ranger/VRX consequence-custody experiments

Instrument the chain:

`Observation -> Inference -> Decision -> Authority/Standing -> Requested Action -> Execution -> Result Observation -> Consequence Attribution`

Use controlled mismatch/fault cases to determine exactly where evidence permits or forbids an independent-verifier conclusion.

### Phase G — Adversarial qualification and independent reproduction

External reviewers should be invited to construct stronger standards-based encodings and counterexamples. Negative results, null results and successful challenges remain first-class research outputs.

## 8. Data and evidence plan

The initial programme does not require a proprietary institutional dataset.

Core research data can be generated prospectively and includes:

- synthetic atomic evidence propositions and dependency graphs;
- formal proof/counterexample traces;
- matched Evidence Architecture and RATS+ outputs;
- system and independent-observer telemetry;
- policy/authority state;
- AI model/runtime and tool-action evidence;
- Ranger/VRX command, actuator and resulting-state observations;
- injected-fault ground truth;
- verifier conclusions and support traces;
- performance/resource measurements.

External organizational datasets may later strengthen ecological validity but are not admission prerequisites for this research design.

## 9. Evaluation criteria

Primary evaluation criteria include:

- unsupported semantic-promotion rate;
- supported-conclusion recall;
- standing-collapse rate;
- command/execution/result/consequence collapse rate;
- independence-collapse rate;
- false-completeness/omission error;
- contradiction preservation;
- conclusion-to-source/policy trace completeness;
- cross-domain consistency;
- formal invariant counterexamples;
- operational overhead;
- external reproduction/challenge.

The research should explicitly report when verification is impossible from available evidence.

## 10. Revised prospective-publication plan

The current preferred sequence is:

1. **Formal non-collapse semantics for bounded machine-action evidence.**
2. **Consequence custody and independent result observation.**
3. **Distributed/offline evidence continuity under explicit assumptions.**
4. **Cross-domain evaluation of non-collapse semantics.**
5. **AI machine-action evidence: attested self-report versus independent observation.**
6. **Ranger/VRX cyber-physical consequence evidence and adversarial qualification.**

The Evidence Object and Evidence Graph should be described as implementation/research substrates unless later evidence justifies restoring a stronger originality claim.

## 11. What remains doctoral work

The following are intentionally **not** complete and should remain part of the doctorate rather than admission prerequisites unless City says otherwise:

- final systematic literature review;
- final originality determination;
- final non-collapse calculus;
- EXP-003 execution;
- EXP-001 human evaluator study;
- Ranger/VRX physical consequence-custody datasets;
- AI nondeterministic replication studies;
- full adversarial campaign;
- independent reproduction;
- peer-reviewed prospective publications;
- final supported/refuted contribution set;
- thesis synthesis.

## 12. Candidate academic profile relevant to entry

The application is not dependent solely on a professional-experience exception. Current records indicate:

- B.S. Information Technology, Colorado State University Global Campus;
- M.S. Cybersecurity, University of Delaware;
- prior Computer Science doctoral study at Missouri University of Science and Technology;
- extensive senior engineering/architecture experience;
- published technical books and Microsoft curriculum authorship;
- substantial professional speaking/training and advanced Microsoft credentials.

Official transcripts and the exact Missouri S&T status wording must be verified before formal application.

## 13. Supervisor targets and outreach status

### Primary — Professor Ilir Gashi

Director, Centre for Software Reliability. Strong fit for software reliability, security, dependability and empirical assessment.

**Status:** initial doctoral-fit/supervision email sent. Response pending.

Profile: https://www.citystgeorges.ac.uk/about/people/academics/ilir-gashi

### Strong alternate/co-supervision — Professor Robin Bloomfield

Fit: software/system dependability, safety and assurance cases, security-informed safety, critical infrastructure and trustworthy software-based systems.

Profile: https://www.citystgeorges.ac.uk/about/people/academics/robin-bloomfield

### Strong alternate/co-supervision — Professor Peter Bishop

Fit: software/system dependability, system safety/security, assurance-case methodology and assurance of autonomous systems.

Profile: https://www.citystgeorges.ac.uk/about/people/academics/peter-bishop

## 14. Independent technical challenge status

A request has been sent to Ned Smith for independent adversarial review of the RATS equivalence analysis.

The request explicitly reports the adverse internal red-team finding and asks the reviewer to defeat remaining ETS differentiation rather than endorse the project.

No validation is claimed until a substantive external response is received.

## 15. Admission/application questions still to resolve

1. Confirm the project may use the Computer Science PhD by Prospective Publication route for the next viable intake.
2. Confirm the next application/start window.
3. Confirm attendance/residency expectations and part-time/remote feasibility for a U.S.-based candidate.
4. Confirm publication expectations for Computer Science: number/type of outputs, venue expectations, authorship rules and handling of collaborative papers.
5. Confirm supervisory team and Centre for Software Reliability fit.
6. Confirm final transcript/qualification treatment.

## 16. Application artifacts — current status

Already created:

- academic CV draft;
- City St George's application dossier;
- university-neutral doctoral proposal;
- contribution ledger;
- experiment ledger;
- literature map/bibliography/gap analysis;
- W3C PROV and RATS closest-work qualification;
- external technical-review package.

Still required:

- official transcripts;
- exact prior-doctoral-study wording;
- 2–3 referees;
- selected immutable public portfolio;
- 1–2 page final contribution summary synchronized with external review;
- route-specific final proposal after supervisor feedback;
- confirmed intake/attendance requirements.

## 17. Current supervisor pitch

A concise current framing is:

> I began with a broad evidence-architecture implementation and have already used prior-art mapping and an adversarial RATS comparison to narrow the research question. Existing standards can encode more of the evidence surface than a weak comparison suggests. The proposed doctorate therefore asks whether a formal non-collapse semantics and consequence-custody discipline provides a measurable, cross-domain verification benefit beyond equally informative rich standards profiles, and under what conditions that benefit disappears. ETS, AI Witness and Ranger/VRX provide the implementation and experimental platforms, but the contribution is allowed to become substrate independent—or to fail.

## 18. Decision rule

Supervisor engagement should continue now.

Do not delay doctoral-home selection for completed empirical datasets, institutional adoption, Ranger hardware completion or peer-reviewed ETS publications. Those are prospective research outputs.

Formal submission should follow once supervisory fit, next intake, attendance feasibility, transcripts and referees are sufficiently resolved.
