# Full ETS / Evidence Architecture Doctoral Listening Edition

**Derivative listening manuscript — not a canonical research artifact**

Source baseline: `ShannonBrayNC/ETS` `main` at `374c0ab32cd1ba0ffda1b75fa561fc075a60fd11`.

Scientific status at this baseline: EXP-001 is **NOT EXECUTED**. EA-C001 and EA-C002 remain **candidate contributions**. Independent fact-equivalence certification is incomplete. No governing institutional human-subjects determination or approval is claimed.

This file is written to be narrated without the repository open. Exact source traceability is maintained in `SOURCE_TRACEABILITY_MATRIX.md`.

---

# Part I — Why This Research Exists

Modern systems are extraordinarily good at producing records. Cloud platforms generate audit logs. Applications emit events. Identity providers record authentication. Security tools preserve alerts. AI systems produce scores and tool calls. Industrial controllers report actions and state. Cameras sign media. Distributed systems calculate hashes, Merkle roots, signatures, attestations, and timestamps.

At first glance, this looks like an abundance of evidence.

But an abundance of records is not the same thing as an ability to reconstruct a consequential event without silently adding assumptions.

That gap is the research problem.

The most important fact about the doctoral program at this point is that its first confirmatory evaluator study, EXP-001, has not been executed. There are no participant responses, experimental effect sizes, confirmatory findings, or statistical outcome from that study. The experiment is preregistered and much of its pre-execution machinery is frozen, but design is not outcome.

EA-C001, the Evidence Object candidate, and EA-C002, the Evidence Graph candidate, also remain candidate contributions. They have been narrowed by prior-art review. Neither becomes an original contribution to knowledge merely because software exists, a schema is formalized, a test passes, or the repository is technically substantial.

The repository contains several distinct forms of evidence and they must not be merged.

A proposed theory says what might be true. A formalized architecture defines terms, boundaries, invariants, and requirements. Implemented engineering shows that a design has been encoded. A bounded formal or mathematical result establishes a property under stated assumptions. A prior-art finding says what earlier work already covers. A preregistered hypothesis states a prediction before outcome data. An unexecuted experiment defines a method without producing empirical evidence. An empirical result exists only after execution and analysis.

These categories can support one another. They are not interchangeable.

## Data, records, provenance, evidence, verification, and proof

Data is the broadest category. A sensor number, model output, timestamp, or log line is data. It may be accurate, stale, incomplete, fabricated, malformed, or valid.

A record is data preserved as an account of an event, state, decision, observation, or transaction. Persistence and structure do not make a record self-proving.

Provenance describes origin, derivation, transformation, responsibility, and process history. Provenance can identify what generated an artifact, what source an output depended upon, who was associated with a process, or what earlier version a record revised.

Provenance is powerful, but it is mature prior art. Evidence Architecture cannot call provenance itself novel.

Evidence is material offered to support or challenge a claim under an explicit trust and interpretation model. Evidence does not become truth merely because it is signed, hashed, logged, or connected in a graph.

Verification is a bounded procedure. A signature can verify. A digest can match. Log inclusion can verify against a root. A policy reference can be checked. A retained authority checkpoint can be assessed for freshness. A claimed result may be compared with a physical observation.

The word bounded matters. Verification of one proposition must not silently imply another.

Proof is even more context-dependent. Mathematical proof, cryptographic proof, legal proof, and ordinary engineering usage are not interchangeable. A Merkle inclusion proof can establish inclusion relative to a tree root. It cannot prove that a physical event occurred, that a person possessed lawful authority, or that every relevant event was captured.

## The compression problem

Operational systems often compress many questions into one status: authenticated, verified, approved, completed, healthy, or no hazard detected.

Those labels can conceal materially different propositions.

A camera can authenticate a capture artifact while the depicted scene remains staged. A model can produce a signed risk score while the underlying condition remains unobserved. Two models can emit two scores while both depend on the same source. A policy can remain cryptographically authentic after it becomes stale. A controller can report an intended state while an independent physical measurement contradicts the intended consequence. A sensor can report nothing because nothing happened, or because the sensor was unavailable.

Missing evidence is therefore dangerous. Absence in a package can mean an event did not happen, an event happened through an uncaptured channel, a connector failed, a source was unavailable, an expected artifact was never defined, or material was omitted.

To infer event absence from evidence absence, the verifier needs an expectation or coverage basis.

The formal ETS work captures this conservatively: omission suspicion is valid relative to an external expected-event set. That does not prove the expectation set itself is complete or authoritative.

The overarching research question is therefore whether an independent verifier can reconstruct and evaluate provenance, identity, authority, policy context, decision, action, result, and remaining uncertainty without simply trusting the system that originated the event.

Independent does not mean omniscient. The verifier can still be limited by weak sensors, compromised keys, incomplete capture, stale checkpoints, poor time synchronization, hidden external channels, or missing policy evidence.

Independence means the evidence and its boundaries are inspectable.

If the strongest defensible conclusion is unknown, the architecture should preserve unknown. If the strongest statement is that an action was accepted but execution is unconfirmed, it should not collapse that into completed. If a record is authentic but stale, authenticity should not become current standing.

That is the problem Evidence Architecture investigates.

---

# Part II — The Evidence Architecture Thesis

Evidence Architecture is not built around the idea that a cryptographic mechanism turns a record into truth. It is built around a stricter proposition: claims should remain bounded by the evidence and mechanisms supporting them.

The central spoken sequence is:

Observed is not the same as authenticated.

Authenticated is not the same as authorized.

Authorized is not the same as executed.

Executed is not necessarily the same as consequential.

And a recorded consequence is not automatically independently verified truth.

Every transition is a place where an evidence system can overclaim.

## Evidence Objects

EA-C001 concerns the candidate Evidence Object model. Its candidate distinction is not a record with a hash. Signed metadata, provenance records, transparency logs, audit trails, and attestation evidence all have extensive prior art.

The intended Evidence Object is a portable evidentiary envelope with an explicit identity boundary and typed bindings to other evidence contracts. The current version-two implementation separates canonical identity-bearing material from proof material that can evolve independently. It supports bindings for events, claims, provenance, context, relationships, policy, privacy, and verification.

That is implemented engineering.

The research question is whether a domain-neutral object that preserves bounded verification dimensions provides a materially distinct and useful semantic contribution.

Instead of one green light called verified, imagine several gauges.

Did the bytes canonicalize as expected? Does the digest match? Does the signature validate under the stated key and trust model? What source identity does that support? What custody history is evidenced? What policy or standing context applies? How fresh is the retained state? What is known about completeness? What consequence is supported? What is explicitly not claimed?

A valid signature may support integrity. It should not automatically establish authority, completeness, freshness, standing, or physical outcome.

## Evidence Graphs

Evidence is relational. An observation can inform an inference. An inference can inform a decision. A decision can depend on policy and authority. A decision can generate a requested action. A target system can accept that action. A mechanism may or may not produce the intended external result. A later observation can support or contradict that result.

EA-C002 concerns the candidate Evidence Graph model.

The graph itself is not novel. W3C PROV and decades of provenance research already provide rich graph models.

The candidate distinction is narrower: consequential relationships may need to be treated as evidence claims whose own source, provenance, verification status, epistemic status, dependencies, and nonclaims remain inspectable.

A line from decision to result is not self-proving.

The graph should preserve whether a relationship is directly evidenced, inferred, contradicted, unavailable, or dependent on a shared source.

This matters when two analytical systems appear to corroborate each other but both depend on the same upstream record. There are two outputs, but not necessarily two independent sources.

## Epistemic states and the epistemic ceiling

Evidence Architecture treats uncertainty as information.

Unknown, not observed, not available, indeterminate, and contradicted are materially different states.

Not observed can mean the observation process ran and did not detect the event. Not available can mean the mechanism could not provide evidence. Unknown means the package does not establish the proposition. Indeterminate means the available evidence cannot distinguish alternatives. Contradicted means material evidence conflicts with a proposition or another evidence item.

The Ranger cyber-physical work adds an important rule: a derived or asserted claim must not exceed the evidentiary strength supported by the mechanisms and evidence available at consequence time.

That is the epistemic ceiling.

A signed media artifact can support device-linked capture provenance without proving scene truth. A model score can support an inference without proving the underlying real-world condition. Motor telemetry can support controller output without proving physical displacement.

Better evidence can raise the ceiling. A claim should not rise above it.

## Reconstruction Boundary

The Reconstruction Boundary asks whether the system can establish what happened, under what conditions, and what remains unknown.

Reconstruction concerns events, artifacts, states, transitions, and outcomes. A well-preserved event may be reconstructable even when the action lacked valid authority.

## Standing Boundary

The Standing Boundary asks whether the material predicates authorizing an action, decision, transition, or consequence held at the relevant time.

Standing may depend on identity, delegated authority, policy version, consent, entitlement, scope, revocation, jurisdiction, validity windows, external conditions, and contradictory evidence.

A reviewer can have a valid identity and role while a required high-value delegation has expired. The signed approval record can remain authentic. The historical identity record can remain true. Yet valid standing for the consequential decision is not established by the expired delegation.

The verifier must also avoid overclaiming in the opposite direction. Failure to establish authority from the supplied evidence does not prove that no lawful authority existed elsewhere.

## Consequence Custody Boundary

The architecture defines a stronger boundary called Consequence Custody. It asks whether the transition from a standing-qualified state into consequence was itself governed and whether that governance can be evidenced.

For implementations that actually claim consequence custody, the normative rule is: no standing, no bind.

This is not a blanket property of every ETS component. A component that captures, preserves, transports, or verifies evidence may help evaluate standing without enforcing it. A standing-aware architecture may evaluate standing and still permit a policy-defined override. Only an implementation that actually makes valid standing a prerequisite to binding a consequence may claim consequence custody.

## Action-result non-collapse

Cyber-physical systems make stage separation vivid.

Decision. Requested action. Accepted action. Controller response. Physical response. Observed result.

These can happen close together and still be different propositions.

An internal controller status is evidence about the controller. An independent physical measurement is evidence about the external state. If they conflict, Evidence Architecture wants the contradiction preserved rather than normalized away.

The thesis is therefore not that ETS proves what happened. It is almost the inverse: Evidence Architecture attempts to make it harder to claim more than the available evidence supports.

If this discipline proves useful under independent evaluation, it may form part of a contribution. If ordinary provenance with domain extensions provides the same benefit, the candidate contribution must narrow.

---

# Part III — Prior Art

A doctoral contribution begins by asking what was already known.

The prior-art work has narrowed the Evidence Architecture novelty surface substantially.

## W3C PROV

W3C PROV is the principal baseline for the Evidence Graph. It already represents entities, activities, agents, generation, usage, derivation, attribution, association, delegation, revision, specialization, invalidation, primary sources, collections, and temporal relationships.

Evidence Architecture therefore cannot claim novelty for typed provenance graphs, artifact-to-process relations, derivation, revision, delegation, provenance of provenance, or domain specialization.

Many ETS relations map directly to PROV, and many observations, inferences, policies, and decision chains can be encoded through PROV entities, activities, attributes, qualified relations, or specialization.

The candidate distinction is not encodability. It is whether added normative semantics—standing separation, epistemic states, relationship-level claims, dimensional verification, and consequence-stage non-collapse—produce measurable reconstruction benefit.

## Provenance semirings and database lineage

Database provenance already provides why-provenance, where-provenance, lineage, source dependency, and algebraic composition through provenance semirings.

ETS cannot claim tracing input influence, source dependency, or compositional provenance as novel.

A shared-source scenario can still be useful experimentally. The candidate question is whether explicit dependency plus bounded epistemic semantics reduces false claims of independent corroboration.

## Scientific workflow provenance

Scientific workflow research already captures execution traces, reproducibility, run comparison, and version-aware reconstruction. PDIFF and related work are important examples.

Evidence Architecture cannot claim workflow traces or provenance-based reproducibility as new.

Its candidate distinction concerns other boundaries such as current standing and external consequence.

## Authorization provenance

Authorization-provenance research already records policy inputs, access-control decisions, delegation, and runtime authorization history. ACCESSPROV and related work make generic authorization provenance an invalid novelty claim for ETS.

The candidate question is whether standing as a distinct verification boundary adds something materially different: identity is not standing, historical delegation is not automatically current standing, and a signed decision is not automatically authorized at the relevant time.

This distinction still needs comparison with trust management, capability systems, reference monitors, and policy-provenance literature.

## Claim and evidence graphs

Structured argumentation and claim-evidence systems already represent claims, evidence, support, challenge, attribution, and provenance. Evidence Architecture cannot claim novelty for linking claims and evidence in a graph.

The candidate is narrower: consequential edges may themselves need attributable evidence, verification state, epistemic state, dependency history, contradictions, and explicit noncausal boundaries.

## Remote attestation

The IETF RATS architecture already separates attesters, evidence, verifiers, attestation results, relying parties, reference values, endorsements, and appraisal policy.

EA-C001 cannot therefore be defended merely as a producer providing evidence to a verifier.

## Software supply-chain provenance

in-toto and related supply-chain systems already provide signed step metadata, authorized functionaries, commands, materials, products, digests, and verification against expected layouts.

Evidence Architecture cannot claim those mechanisms as novel, and applying them to a broader domain is not by itself a contribution to knowledge.

## Transparency and secure logs

Certificate Transparency and secure-audit literature already provide append-only logs, Merkle-based inclusion and consistency, signed roots, and tamper-evident histories.

Those are foundations, not ETS novelty.

A perfectly protected record can still preserve a bad observation. A cryptographically valid stale checkpoint is still stale. A protected action record does not prove external consequence.

## AI and machine-learning provenance

AI and ML provenance already covers training-data lineage, model genealogy, pipeline provenance, deployment history, and model records.

ETS cannot claim that recording model versions and inputs is a novel AI accountability framework.

The candidate machine-action question is whether evidence can preserve observation, inference, policy, authority, decision, tool or action request, acceptance or execution, consequence, and result observation without inventing hidden reasoning.

For nondeterministic systems, evidence replay need not mean reproducing an identical hidden output. It can mean reconstructing the inspectable inputs, runtime identity, authority, tools, declared outputs, and consequences.

## Cyber-physical provenance, runtime assurance, and safety cases

Control provenance, runtime assurance, safety interlocks, reference-monitor concepts, and structured assurance cases all predate ETS.

Evidence Architecture cannot claim those fields generally.

The remaining candidate distinction is the integrated semantic rule that requested action, accepted action, execution, consequence, and result observation are not equivalent propositions, together with standing and consequence-custody boundaries. Even that candidate requires deeper comparison to existing cyber-physical and assurance research.

## The narrowed candidate surface

After prior-art exclusions, the researchable surface is smaller: dimensional verification vectors; first-class epistemic states and nonclaims; standing as a separate boundary; action-to-consequence non-collapse; consequence custody as a separately qualified boundary; relationship-level evidentiary claims; and shared-source dependence used to prevent false corroboration.

None is established as an original contribution simply because ETS names it.

If equivalent prior work is found, narrow or retire the claim. If strong domain-extended PROV performs as well as Evidence Architecture, the EA-specific benefit weakens. If the added semantics impose cost without reducing error, that is evidence against the current framing.

Prior art is not an obstacle. It is the filter that turns a broad system idea into a falsifiable scientific question.

---

# Part IV — Candidate Contributions

## EA-C001

The problem for EA-C001 is semantic inflation: one verified dimension is treated as if many other dimensions were also verified.

The prior-art baseline is extensive: PROV, RATS, in-toto, transparency logs, secure audit systems, and digital chain-of-custody methods.

The narrowed candidate is a domain-neutral Evidence Object whose verification result is decomposed into bounded dimensions and whose nonclaims remain explicit. The implemented version-two object has an explicit identity boundary and typed contract bindings; that is engineering evidence, not novelty evidence.

The falsifiable hypothesis H-C001-A predicts that a dimensional Evidence Object result will produce fewer unsupported semantic inferences than an otherwise equivalent binary verification result.

EA-C001 would become stronger with deeper systematic prior art, a minimum-sufficiency argument, independent implementation or reproduction, and empirical evidence that the bounded semantics reduce errors without adding facts.

It would weaken if prior work already integrates equivalent semantics, if the strong domain-extended baseline performs as well, if training burden erases the benefit, or if the model remains a useful packaging convention without a measurable epistemic advantage.

## EA-C002

The problem for EA-C002 is that consequential relationships can be represented in a graph without the edge itself carrying enough evidence to justify the interpretation placed on it.

The prior-art baseline includes W3C PROV, database provenance, workflow traces, claim-evidence graphs, authorization provenance, and cyber-physical control provenance.

The narrowed candidate treats important relationships as separately inspectable claims, preserving producer, provenance, verification status, epistemic state, dependency, contradiction, standing, and noncausality where applicable.

H-C002-A predicts that attributable relationship evidence improves reconstruction precision compared with unqualified topology.

H-C002-B predicts that explicit unknown, unavailable, indeterminate, and contradicted states reduce errors caused by treating missing evidence as false or absent.

H-C002-C predicts that separating decision, request, acceptance or execution, and result observation reduces incorrect outcome attribution.

EA-C002 strengthens if rigorous relation mapping and independent evaluation show that these semantics add value across domains. It weakens if ordinary domain-extended PROV performs equivalently, if the metadata adds cognitive burden without reducing errors, or if deeper prior art already integrates equivalent semantics.

Falsifiability is a strength because the candidate is allowed to lose.

EXP-001 includes Condition B specifically to test whether ordinary domain extension explains the apparent value. If B performs as well as C, the research must say so.

---

# Part V — EXP-001 Design

EXP-001 is the Bounded Evidence Graph Reconstruction Comparison.

Its question is whether, with underlying facts held constant, an Evidence Architecture representation reduces unsupported reconstruction conclusions relative to established provenance representations.

It is not a truth experiment, a legal-admissibility experiment, a cryptographic novelty experiment, or a universal test of PROV. It has not been executed.

## Conditions A, B, and C

Condition A uses ordinary W3C PROV-compatible provenance concepts. It is not intentionally starved of facts. Material information can still be represented as entities, attributes, or relationships when necessary.

Condition B uses provenance plus strong domain extensions. It may explicitly represent authorization state, policy versions, sensor availability, model output, action acceptance, physical observation, source dependence, contradiction, revocation, and quality metadata. What it lacks is the Evidence Architecture normative discipline as a required interpretation rule.

Condition C contains the same substantive facts but explicitly presents Evidence Architecture boundaries: observation versus inference; integrity versus identity versus standing; historical versus current standing; evidence absence versus evidence of absence; source dependence; requested versus accepted or executed action; consequence versus result observation; contradiction; time quality; and explicit nonclaims.

Condition C is not allowed to receive extra reconstruction-material facts.

## Fact equivalence

Every scenario has a frozen fact inventory. An independent reviewer must determine whether all three representations preserve the same reconstruction-material facts while differing in the intended semantic representation.

That independent review remains incomplete.

The author can perform internal quality assurance, but author-only review does not satisfy the independent gate.

## Evaluator task

Each evaluator sees all twelve scenarios, one condition per scenario, and answers the same six questions:

What events or states are directly supported?

What conclusions are inferred?

Which actor or action had valid standing, if established?

What was requested, what was executed, and what consequence or result was observed?

What remains unknown, unavailable, contradictory, stale, or unverified?

What is the strongest defensible overall conclusion without exceeding the evidence?

Evaluators also provide confidence, and response time may be recorded. Unknown and indeterminate are valid answers.

## Randomization and balance

The preregistration targets at least twelve evaluators if feasible. The frozen design contains twelve prospective evaluator slots. Each slot receives four A, four B, and four C scenarios. Across all slots, each scenario appears four times in each format.

The base allocation is cyclic: add the zero-based evaluator index and scenario index, then take the remainder after division by three.

A pseudorandom seed was frozen before outcome data. It controls presentation order and opaque evaluator-facing format labels. The exact seed and mapping belong in the written reference artifacts, not the narration.

Assignments cannot be adaptively optimized after seeing performance.

## Thirty-six frozen packets and the hash discrepancy

Twelve scenarios times three representations gives thirty-six evaluator packets.

The packet-freeze process discovered that an early expected SHA-256 manifest did not match regeneration from the committed packet source and renderer.

The repository did not silently replace the failed manifest.

It preserved the discrepancy as a pre-execution integrity record.

Because no evaluator had been exposed and no outcome data existed, the correction could remain prospective.

The packets were regenerated in a clean pass and then generated again. Both passes produced thirty-six packets. The two hash sets were identical.

That passed the deterministic-render gate, and a new authoritative hash manifest became the operational reference. The failed expected manifest remains as historical evidence.

This freeze proves byte reproducibility of the packet rendering. It does not prove fact equivalence, scientific validity, independent certification, human-subjects approval, or an experimental result.

---

# Part V — The Twelve Scenarios

## Scenario One: expired delegated authority

A benefit reviewer has a valid identity and Senior Reviewer role and signs approval of a thirty-one-thousand-five-hundred-dollar claim. The supplied delegation for approvals above twenty-five thousand dollars expired two days earlier. No replacement delegation is present. A payment instruction exists; settlement does not.

The evidence supports identity, role, record integrity, expired supplied delegation, and the generated instruction. It does not establish the required high-value standing from the supplied delegation, does not prove no other authority existed elsewhere, and does not establish settlement.

## Scenario Two: missing finance approval

A purchase above one hundred thousand dollars requires both Procurement and Finance approval. Procurement approval is present. Finance approval is absent. But the capture system reports only ninety-two percent ingestion availability because a connector was degraded.

Absence from the package is supported. Nonoccurrence of Finance approval is not established.

## Scenario Three: two scores from one source

Two analytical models produce elevated scores, but both materially depend on the same address-mismatch source. Both outputs are signed.

There are two inferences, not necessarily two independent confirmations. Neither score is direct observation of the underlying real-world condition.

## Scenario Four: authentic stale policy

A signed policy version is later superseded. The older version remains cryptographically authentic and can be retrieved from a valid archive.

Authentic historical content does not establish that the old version remained operative after supersession.

## Scenario Five: AI recommendation and human decision

An AI model recommends denial. Policy requires a human decision. An authorized human reviews and approves the denial. A notice is generated, but delivery is not proved.

Model recommendation, human decision, notice generation, and delivery are separate propositions.

## Scenario Six: accepted action, execution unconfirmed

An authorized automated process requests an account-state change. The target service returns an accepted-for-processing status. No completion event exists. A later event remains consistent with the old state.

Acceptance is supported. Completed execution is not. The later evidence contradicts an assumption of immediate completion.

## Scenario Seven: authentic capture and scene truth

A registered camera signs an artifact and the digest matches. A synthetic-media detector produces a high likelihood score. No independent source proves whether the scene was staged, generated, or post-processed.

The signature supports capture provenance under the device trust model. The detector supports an inference. Neither proves scene truth.

## Scenario Eight: unavailable sensor

Sensors A and B report no hazard. Sensor C, the only sensor covering the east enclosure, is offline. The system reports no hazard detected.

The supported conclusion is bounded to the observed coverage. The east enclosure remains unobservable. No detection is not the same as proof that no hazard existed.

## Scenario Nine: Ranger motion request and displacement

An authorized operator requests Ranger motion. The safety controller accepts it. Motor current is nonzero. The wheel encoder is degraded and there is no independent position observation.

The request, acceptance, and motor output are supported. Physical displacement is not established.

## Scenario Ten: breaker state and physical consequence

A protection system requests a breaker state change and the controller reports the target state. An independent current transformer continues to measure load for a period. Later inspection identifies a mechanical linkage problem.

The requested and reported controller states are supported. Immediate successful physical consequence is contradicted by the independent measurement.

## Scenario Eleven: uncertain clocks

Two signed systems record nearby events. One clock has tight uncertainty. The other lost synchronization and has much wider possible drift.

The records are intact, but their apparent millisecond ordering is not established. A signature protects the record; it does not repair the clock.

## Scenario Twelve: stale authority checkpoint

A key is valid at an earlier signed authority checkpoint and later revoked. A verifier receives the old checkpoint while independently retaining newer authority state.

The old checkpoint remains authentic but stale. Historical validity does not establish current authorization.

## What the scenarios collectively teach

Identity is not authority. Authenticity is not currentness. Missing evidence is not automatically nonoccurrence. Multiple dependent outputs are not independent corroboration. Inference is not observation. Recommendation is not decision. Acceptance is not execution. Controller state is not physical consequence. Timestamp precision is not time accuracy. Historical validity is not current standing.

Condition B may be able to communicate these distinctions adequately. That is why it exists.

---

# Part VI — Measurement and Analysis

EXP-001 preregisters specific error measures rather than a subjective impression of clarity.

Unsupported inference measures conclusions stronger than the evidence.

Standing collapse measures identity, signature, integrity, or inclusion being treated as sufficient authorization.

Command-result or action-result collapse measures requests, acknowledgments, internal state, or execution being treated as proof of later consequence.

False completeness measures missing evidence being converted into proof that the underlying event did not occur.

Missed contradiction measures failure to recognize material conflicting evidence.

Epistemic overstatement measures unknown, unavailable, or indeterminate evidence being upgraded into a positive or negative fact.

Supported-claim precision asks what proportion of asserted conclusions are actually supported, preventing a trivial strategy in which evaluators avoid errors by saying almost nothing.

Reconstruction time measures cognitive cost. A representation can be more accurate yet too burdensome, or faster but more error-prone.

Secondary measures include recognition of shared-source dependence, observation versus inference, stale versus current state, time quality, contradiction, confidence calibration, and differences by evaluator stratum.

Where responses are double-scored, raw agreement and an appropriate chance-corrected statistic may be calculated if the sample supports it. Original scorer judgments should be preserved separately from adjudication. Poor agreement is itself a result.

## Confirmatory rule

Condition C must show a lower aggregate rate than both A and B on at least three of four core boundary errors: unsupported inference, standing collapse, action-result collapse, and false completeness; and it must not materially worsen supported-claim precision.

This threshold may not be reinterpreted after seeing data.

If C beats A but not B, ordinary domain extension may explain the benefit and the EA-specific claim weakens.

## Null and negative results

If A, B, and C perform similarly, the current hypothesis is not supported by that experiment.

If B performs as well as C, ordinary domain-extended provenance may be sufficient for the tested reconstruction tasks.

If C lowers some errors but increases others materially, that tradeoff must be reported.

If C substantially increases reconstruction time, that matters.

If effects appear only in one evaluator group, generalization must narrow.

If ordinary PROV already communicates some boundaries adequately, that negative finding must remain visible.

If scoring ambiguity produces poor agreement, the metric may need reconsideration.

These outcomes can narrow, leave unresolved, or refute parts of EA-C001 and EA-C002.

## A current pre-execution implementation-alignment issue

The frozen scoring key defines several rates using trap-specific or proposition-specific denominators. Standing collapse is defined over scenarios with standing traps. Action-result collapse is defined over scenarios with action-stage traps. False completeness is defined over missingness or capability traps. Other error categories also have specified denominator logic.

The current Python descriptive-analysis implementation appears to use all substantive scored assertions as the denominator for every error metric in its error-fields loop.

That is a source-level implementation-alignment issue, not an experimental finding.

No participant data exist, so it can still be reconciled prospectively. The correct research action is to align the executable analysis with the frozen metric definitions, document the resolution, and freeze the implementation before participant outcome data—not to choose formulas after seeing results.

Descriptive reporting is mandatory. Inferential statistics are optional and must fit the repeated or matched design, include effect sizes and uncertainty, address multiplicity, and never be chosen simply because they yield a favorable p-value.

---

# Part VI — Research Integrity

The research program should apply Evidence Architecture principles to itself.

Prospective records must be distinguished from retrospective reconstruction. Retrospective work is legitimate when labeled accurately. It must not be presented as preregistration.

EA-C001 and EA-C002 are retrospective candidate contributions. EXP-001 is a prospective experiment registered before evaluator outcomes.

Negative evidence must be preserved: failed experiments, failed hypotheses, counterexamples, anomalies, null results, inconclusive results, and known unsupported cases.

The packet-hash discrepancy is a worked example. The first expected manifest failed. The failure record remained. The later authoritative freeze was established prospectively through two matching regeneration passes. The history was not rewritten.

The repository also distinguishes engineering verification, formal evidence, research experiments, and external reproduction.

A unit test can demonstrate implementation behavior. A formal model can establish a bounded property under assumptions. A participant study can evaluate a hypothesis. Independent reproduction asks whether someone else obtains the result. Independent challenge tests the failure boundaries.

Formal ETS artifacts support restrained properties such as deterministic hashing, append-only behavior, omission suspicion relative to an external expected-event set, fork suspicion, bounded asynchronous classifications, and fairness-scoped liveness.

Those do not prove real-world truth, legal sufficiency, complete capture, private-key safety, Byzantine consensus, Internet-scale liveness, or election correctness.

The formal theorem appendix itself describes implementation-facing proof obligations rather than blanket mathematical-publication claims. Reproducibility material similarly distinguishes internal repeatability from independent reproduction.

The self-referential rule is simple: if a gate is pending, preserve pending. If approval does not exist, do not say approved. If a freeze failed first, preserve the failure. If analysis code does not align with the frozen formula, record the mismatch before execution. If prior art weakens a candidate contribution, narrow the claim.

Research integrity is Evidence Architecture applied to the research process.

---

# Part VII — Independent Review and Human Subjects

Two external gates remain essential before confirmatory participant exposure: independent fact-equivalence review and institutional human-subjects determination.

## Independent fact-equivalence review

An independent reviewer must compare each three-format scenario triplet against the frozen fact inventory.

The reviewer checks that every reconstruction-material fact appears across conditions, no condition adds a material fact, unknowns remain unresolved where appropriate, local timestamps are not upgraded into trusted time, identity is not upgraded into authority, authority is not upgraded into standing, action acknowledgment is not upgraded into execution, execution is not upgraded into consequence without evidence, source dependence and contradictions are preserved, absence is not converted into nonoccurrence without a coverage basis, wording does not add truth or causality, and formatting does not materially privilege one condition beyond the intended semantic manipulation.

Each scenario receives pass, fail, or pass with documented nonmaterial difference. A fail blocks confirmatory use until corrected prospectively.

The author can perform quality control but cannot certify his own review as independent. Author-only review remains author-only and not confirmatory ready.

The repository contains handoff instructions and review scaffolding. No scenario has yet been independently certified.

## Human-subjects determination

EXP-001 is designed as systematic research intended to contribute to generalizable knowledge and prospectively collects analyzable responses from living adult evaluators. The design may collect free-text answers, confidence, response time, evaluator code, and broad experience strata.

The project therefore conservatively treats the study as potentially human-subjects research until the governing institution decides the applicable pathway.

The repository does not determine that the experiment is exempt, non-human-subject research, expedited, or approved by an Institutional Review Board.

De-identification can reduce privacy risk, but it does not automatically settle the regulatory question because participant interaction itself may be relevant.

The repository has prepared an institutional review packet, a cover memo requesting written determination, and a participant-information draft. These are preparation artifacts, not approvals.

The participant draft deliberately does not invent approved duration, compensation, final consent language, retention policy, or institutional contacts.

Human evaluator recruitment is blocked pending institutional determination and any resulting requirements for consent or information, training, privacy, retention, recruitment, compensation, or affiliation.

No participant response or outcome data exist.

---

# Part VIII — What Happens Next

The remaining gates should occur in chronological order.

First, complete independent fact-equivalence review for all twelve scenario triplets. Preserve any failure and correct material inequivalence prospectively before exposure.

Second, obtain the governing institutional human-subjects determination. Satisfy any required participant-information, consent, training, privacy, retention, recruitment, compensation, or affiliation controls.

Third, resolve pre-execution control mismatches, including the current analysis-formula implementation issue, without using outcome data to choose the resolution.

Fourth, record the final pre-execution repository commit and authoritative artifact references after the external gates are complete.

Fifth, recruit evaluators under the approved or accepted protocol. Use the frozen assignment slots rather than adapting assignments to early performance.

Sixth, execute EXP-001 by collecting actual responses. Until this step occurs, there are no empirical results.

Seventh, score the responses using the frozen claim labels and error taxonomy. Preserve double-scored judgments and adjudication separately. Preserve poor agreement.

Eighth, run the preregistered descriptive analysis and evaluate the confirmatory success rule exactly. Add inferential statistics only when justified.

Ninth, publish the method and result together, including negative findings, deviations, limitations, and artifact provenance.

Tenth, package the work for independent reproduction and later independent challenge.

Eleventh, reconsider EA-C001 and EA-C002 in the contribution ledger. They may strengthen, remain candidate, narrow, be revised, or be retired.

The decision should follow the evidence.

---

# Part IX — Doctoral Significance

A large software project is not automatically a doctorate.

A doctoral contribution requires a defensible contribution to knowledge, positioned against prior work, supported by explicit method, evaluated under meaningful controls, and bounded by limitations.

ETS can be considered as several contribution classes.

## Engineering

The engineering class is comparatively mature. The repository includes a reference implementation, Evidence Object models, canonicalization and hashing, append-only logging, verification primitives, formal artifacts, asynchronous experiments, AI Witness work, Ranger research, reproducibility instructions, and experiment-support tooling.

Engineering demonstrates feasibility. It does not establish novelty by itself.

## Conceptual

The conceptual class includes bounded verification, epistemic states, Reconstruction Boundary, Standing Boundary, consequence-stage non-collapse, consequence custody, shared-source dependence, and explicit nonclaims.

These form a coherent thesis, but they must survive comparison with provenance, authorization, attestation, runtime assurance, safety, and argumentation research.

## Formal and mathematical

The formal corpus contains deterministic implementation claims, safety models, bounded asynchronous models, fairness-scoped liveness, omission relative to expectation, and probabilistic primitives such as Beta-Bernoulli updating.

It is methodologically significant but explicitly bounded. Stronger doctoral formal work would need tighter refinement from architectural semantics to formal models to implementation and mechanically checked proof obligations. Formalizing epistemic and standing boundaries may be especially important.

## Empirical

The empirical class is the largest missing evidence category for EA-C001 and EA-C002. EXP-001 is designed to begin filling that gap. It has not yet produced participant data.

A defensible empirical contribution requires completed external gates, execution, transparent scoring, preregistered analysis, preservation of null results, and later replication.

## Reproducibility

The repository connects claims to code, tests, models, hashes, frozen artifacts, and reproduction instructions. The packet discrepancy and two-pass freeze are a useful research-provenance example.

But internal repeatability is weaker than independent reproduction, and independent reproduction is weaker than independent challenge.

## Standards and ecosystem

The long-term standards question is whether bounded evidence semantics can interoperate across enterprise systems, AI agents, government workflows, cybersecurity, autonomous systems, and other high-consequence environments.

A standards contribution would have to be earned through stable profiles, conformance suites, independent implementations, external use, prior-standard comparison, and evidence of interoperability benefit.

## Ranger as a research platform

Ranger forces the theory across the digital-physical boundary.

A motion request is not motion. Motor output is not displacement. A classifier result is not human identity. A sensor timeout is not a negative observation. A policy decision is not an actuator result. A physical consequence requires observation through mechanisms whose availability, timing, uncertainty, calibration, and integrity are themselves bounded.

Ranger is therefore a strong future reference platform for cyber-physical provenance and consequence custody. But physical experimental data, independent observation, controlled faults, and external reproduction remain future evidence.

## What is still missing

The candidate novelty surface still needs deeper publication-quality scholarly synthesis.

Peer-reviewed foundational ETS publications are not established in the current research record.

Independent academic review and broad independent reproduction are not established.

Impact evidence must come from independent citation, use, reproduction, challenge, standards work, or scholarly uptake rather than popularity metrics.

Authorship and contribution records need completion for public works.

Formal refinement and broader checked proof coverage remain incomplete.

EXP-001 still requires independent equivalence review, institutional determination, pre-execution reconciliation, execution, scoring, analysis, publication, and later replication.

The public-works manifest is a candidate inventory, not a university acceptance decision.

The defensible position today is that ETS is a coherent research program with substantial engineering, formal artifacts, narrowed candidate contributions, a prospective experiment, and explicit integrity controls. External and empirical evidence must determine which parts become defensible contributions to knowledge.

---

# Part X — Closing Lecture

Return to the central question.

When a system says something happened, what evidence allows an independent party to determine what was observed, inferred, authorized, decided, executed, consequential, preserved, and ultimately verifiable?

The question becomes more important as software acquires more authority over the world.

An AI agent can alter a digital system. A cloud automation system can change account state. A lending model can influence a denial. An industrial controller can change equipment state. An autonomous vehicle can change direction. Ranger can request actuator motion. A government workflow can approve or deny a benefit. A cybersecurity system can isolate a host.

In each case, the originating system can produce a log.

A log is only the beginning.

What did the system observe? Was the observation mechanism available and healthy? Was the observation direct or inferred? What source did the inference depend on? Were apparently independent sources actually dependent? What policy was in force? What authority existed at the relevant time? Was that authority current or only historically valid? What decision was produced? What action was requested? Was it accepted? Was it executed? What happened externally? What observation supports the claimed result? What contradicts it? What remained unobservable? How good were the clocks? How fresh were the authority checkpoints?

Can an independent verifier reconstruct those distinctions without trusting a single success flag from the originating system?

## AI agents

For an AI agent, Evidence Architecture does not require a fictional transcript of hidden reasoning. It asks for externally inspectable evidence: inputs, model or runtime identity, policy and authority, declared recommendation or decision, tool or action request, target acknowledgment, and independently observed resulting state.

A model statement that an action completed is not sufficient. A target acknowledgment may establish acceptance without completion. A later independent observation can be more probative about the resulting state.

## Ranger and autonomous systems

Ranger makes the same epistemic problem physical.

If an authorized operator requests motion, the controller accepts it, and the motors draw current, did Ranger move?

Without position or equivalent physical observation, displacement remains unestablished.

As hardware improves, evidence can become stronger through encoders, inertial measurement, lidar, vision, external beacons, synchronized clocks, actuator feedback, and independent observers.

The evidence theory should remain stable. Better hardware should create stronger evidence, not a different definition of evidence.

## Government accountability

A signed administrative decision can be authentic while its specific delegation is expired. A missing approval can be suspicious without proving nonoccurrence. An authentic policy can be stale.

Evidence Architecture can support accountability while also protecting due process by preserving legitimate uncertainty rather than converting every gap into wrongdoing.

## Cybersecurity

An alert is not an incident. A detection is not ground truth. An isolation request is not proof of isolation. A signed log is not proof of complete capture. A missing event is not an omission finding without expectation or coverage. Two detections are not independent corroboration if they share one source.

## Enterprise systems

Purchases, payments, contracts, account provisioning, policy publication, AI recommendations, human overrides, messages, and records all contain authority and consequence chains. Operational systems can execute them. The evidentiary question is whether a later independent party can reconstruct each stage and the standing under which it occurred.

## The strongest defensible research statement today

Evidence Architecture has not been experimentally proven by EXP-001. EXP-001 has not been executed.

The repository defines a coherent candidate theory, implements substantial pieces, connects parts to formal and reproducibility artifacts, has narrowed novelty claims through prior art, and has preregistered a falsifiable experiment with strong controls.

The internal deterministic packet and assignment freezes are substantially complete. Independent fact-equivalence certification is incomplete. Institutional human-subjects determination is absent. Human recruitment is blocked. No participant outcome data exist.

EA-C001 remains candidate.

EA-C002 remains candidate.

That is the correct location of the evidence today.

Evidence Architecture is ultimately a discipline of refusal.

Refusal to call integrity truth.

Refusal to call identity authority.

Refusal to call historical authority current standing.

Refusal to call missing evidence evidence of absence without a coverage basis.

Refusal to call dependent outputs independent corroboration.

Refusal to call a recommendation a decision.

Refusal to call acceptance execution.

Refusal to call controller state physical consequence.

Refusal to call timestamp precision time accuracy.

Refusal to call a preserved record complete history.

And refusal to call a candidate research contribution established before the evidence exists.

That discipline is constructive because it identifies what additional evidence would be needed for a stronger claim.

If a result is unknown, state what is missing. If standing is not established, identify the unmet predicate. If consequence is unobserved, identify the missing observation. If sources are dependent, preserve the shared lineage. If clocks are uncertain, bound the ordering. If evidence conflicts, preserve the contradiction.

The objective is not to make machines infallible. It is to make their claims reconstructable, challengeable, and bounded.

The doctoral question can therefore be heard as a final challenge:

Can we design systems whose evidence lets an independent party determine not only what the system claims happened, but what was actually observed, what was inferred, what authority existed, what decision occurred, what action was requested, what was executed, what consequence was observed, what remained uncertain, and why the verifier is justified in believing exactly that much—and no more?

That is the research program.

The next answer has to come from evidence.
