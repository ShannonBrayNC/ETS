# ETS Doctoral Contribution Ledger

This ledger records candidate contributions to knowledge. A contribution is not established merely because code or documentation exists.

## Contribution record schema

Each contribution should use this structure:

```text
ID: EA-C###
Title:
Status: candidate | supported | revised | refuted | retired
Record type: prospective | retrospective
Research questions:
Claim:
Problem addressed:
Prior art / related work:
Identified gap:
Difference from prior art:
Formal definition/model:
Methodology:
Implementation evidence:
Experiment IDs:
Results:
Negative results / counterexamples:
Assumptions:
Limitations:
Public artifacts:
Publication target/status:
Independent validation:
Impact evidence:
Authorship/contribution:
First documented:
Last reviewed:
```

## Research-integrity status after RATS qualification

The September 2026 RATS qualification work materially narrowed several early Evidence Architecture claims.

The internal EXP-002 red-team was intentionally configured to give RFC 9334 RATS a strong baseline: rich Claims, multiple Attesters and Verifiers, historical policy intervals, source/derivation identifiers, rich Attestation Results, uncertainty/availability claims, and independent Relying Party policy. Under that internal challenge, every frozen S01-S20 scenario was provisionally representable through direct RATS semantics or an ordinary application profile; no scenario was provisionally classified `NOT_EQUIVALENT`, and no mandatory R+ extra rule was identified in the internal pass.

That is not an independent result and does not close EXP-002. External RATS/attestation review has been requested. However, it is already sufficient to reject broad working claims that an Evidence Object, a dimensional verifier, rich evidence claims, or attested machine-action receipts are themselves likely to constitute the doctoral contribution.

The strongest remaining thesis surface is therefore narrower:

1. formal **non-collapse semantics** that prevent unsupported promotion across evidence dimensions;
2. measurable reduction of category errors when the same facts are represented under those semantics;
3. explicit **consequence custody**, in which requested action, execution, result observation, and causal/consequence claims remain separate propositions;
4. cross-domain generalization of those rules across administrative, AI, distributed, and cyber-physical systems; and
5. negative results showing where ordinary standards profiles already achieve equivalent behavior.

## Candidate contribution inventory

### EA-C001 — Evidence Object model

- **Status:** revised
- **Record type:** retrospective
- **Research questions:** RQ1, RQ3
- **Original candidate claim:** ETS provides a bounded Evidence Object model for independently evaluating identity, integrity, provenance, custody, and declared verification context while separating those properties from semantic truth.
- **Revised candidate claim:** the Evidence Object is primarily an implementation vehicle for a bounded verification semantics. Any doctoral contribution must lie in a formally specified and empirically useful non-collapse discipline, not in the existence of an evidence envelope, verifier role, signed metadata, rich claims, attestation result, or provenance container.
- **Existing evidence:** protocol contracts, canonicalization/hash implementation, verifier tests, formal traceability matrix.
- **Prior-art qualification:** W3C PROV, RATS, in-toto/SLSA-style supply-chain evidence, transparency logs, secure audit logs, attestation architectures, and 2026 RATS work on application-layer action evidence and attested inference receipts substantially constrain primitive-level novelty.
- **EXP-002 negative evidence:** the internal strongest-RATS construction provisionally represented all 20 frozen scenarios without identifying an ETS-only primitive. This is adverse evidence against broad EA-C001 differentiation and must remain in the record.
- **Residual research gap:** whether an explicit, domain-neutral non-collapse calculus can prevent unsupported semantic promotion more reliably than an equally informative but unconstrained rich-profile representation.
- **Primary gaps:** external RATS review; formal rule system; minimum-sufficiency argument; substrate-independent implementation; prospective evaluation under EXP-001/EXP-003; independent reproduction.

### EA-C002 — Evidence Graph model

- **Status:** revised
- **Record type:** retrospective
- **Research questions:** RQ2, RQ3
- **Original candidate claim:** typed graph relationships can make derivation, custody, authority, observation, decision, action, and consequence claims separately inspectable and verifiable without asserting truth merely from graph membership.
- **Revised candidate claim:** no novelty is claimed for typed provenance graphs or qualified relations. The remaining candidate is a relationship-level non-collapse discipline in which evidentiary edges can carry attribution, epistemic state, contradiction, dependency/independence information, policy/standing context, and explicit limits on causal or consequence inference.
- **Existing evidence:** existing architecture/research corpus; Ranger relationship modeling; W3C PROV relation mapping.
- **Prior-art qualification:** W3C PROV already provides rich typed and qualified provenance relations and provenance-of-provenance. Ordinary domain extension may encode much of the remaining metadata.
- **Residual research gap:** whether explicit relationship-level epistemic and independence semantics produce a measurable or formally demonstrable benefit beyond ordinary PROV/domain-profile practice.
- **Primary gaps:** external closest-work review; formal graph inference rules; shared-source independence model; prospective comparison in EXP-001/EXP-003.

### EA-C003 — Explicit trust and claim-boundary decomposition

- **Status:** revised
- **Record type:** retrospective for the original engineering concept; prospective for the narrowed research claim
- **Research questions:** RQ3, RQ7
- **Original candidate claim:** verification outputs can preserve useful cryptographic/procedural guarantees while explicitly retaining unsupported external assumptions instead of collapsing integrity into truth.
- **Revised candidate claim:** a machine-checkable non-collapse semantics can preserve independently supported propositions while preventing inference across unsupported boundaries such as integrity -> truth, identity -> authority, current authority -> historical standing, command -> execution, execution -> result observation, agreement -> independence, and observed result -> causal attribution.
- **Existing evidence:** conservative claim boundaries in research documentation, formal traceability, EXP-001 design, EXP-002 preregistration and internal red-team.
- **Prior-art qualification:** RATS and ordinary application profiles can encode rich claims, policy, uncertainty, provenance, freshness, and authorization semantics. The research claim therefore cannot be merely that these distinctions are representable.
- **Residual research gap:** whether a formal cross-domain rule set that makes forbidden promotions explicit and mechanically enforceable reduces unsupported conclusions without materially suppressing supported conclusions.
- **Primary method:** EXP-003 will compare an unconstrained rich-profile baseline, the non-collapse calculus, and a RATS+ implementation of the same rules. If RATS+ matches the calculus, that supports a substrate-independent rule contribution rather than an ETS-specific architecture claim.
- **Primary gaps:** formal semantics; generated adversarial corpus; model/property verification; independent replication; publication-grade comparison.

### EA-C004 — Offline/asynchronous evidence continuity

- **Status:** candidate
- **Record type:** retrospective
- **Research questions:** RQ4
- **Candidate claim:** bounded evidence provenance can remain independently verifiable through asynchronous transport, reordering, partition, and later synchronization under explicit fairness and healing assumptions.
- **Existing evidence:** `ETSAsyncNetwork.tla`, liveness model, async network implementation/tests, reproducibility work.
- **Primary gaps:** refinement mapping; closest distributed-systems prior-art analysis; wider adversarial evaluation; publication-grade experiments.

### EA-C005 — AI Witness / machine-action provenance

- **Status:** revised
- **Record type:** retrospective for architecture; prospective for the narrowed research claim
- **Research questions:** RQ5, RQ7
- **Original candidate claim:** consequential AI actions can be evidenced through externally inspectable inputs, model/runtime identity, policy, declared decisions, authority, actions, and results without claiming access to or fidelity of hidden internal reasoning.
- **Revised candidate claim:** AI Witness is an implementation and experimental platform for testing bounded machine-action evidence, especially the boundary between attested self-report and independently observed external consequence.
- **Prior-art qualification:** current RATS work on attested inference receipts and application-layer action evidence materially narrows claims around binding model identity, input/output hashes, telemetry, platform attestation, action, authority, and outcome fields.
- **Residual research gap:** independent-verifier semantics for distinguishing attested machine self-report from independently observed external effect, preserving uncertainty and authority context, and integrating consequence custody without hidden-chain-of-thought claims.
- **Existing evidence:** ETS architecture and AI Witness research/case studies.
- **Primary gaps:** external standards review; prospective agent experiment; independent observer; deliberate mutation/omission; nondeterministic replication; comparison against current attestation/action-evidence profiles.

### EA-C006 — Cyber-physical decision provenance

- **Status:** candidate
- **Record type:** retrospective for concept; prospective for future Ranger experiments
- **Research questions:** RQ6, RQ8
- **Candidate claim:** a cyber-physical evidence chain can keep observation, inference, decision, authority, requested action, execution evidence, resulting-state observation, and consequence attribution separately evaluable so an independent verifier can identify which boundaries are supported and which remain asserted or unknown.
- **Existing evidence:** Ranger research program; governed-authority evidence work; VRX/Ranger digital-to-physical consequence-custody scenarios.
- **Prior-art boundary:** the contribution cannot be merely recording a control path, signed command, actuator acknowledgement, runtime-assurance event, or attested action receipt. Existing provenance and assurance systems already cover substantial portions of that surface.
- **Residual research gap:** cross-boundary evidence semantics and independent result observation at the digital-to-physical boundary, especially when command intent, actuator claims, and physical outcome disagree.
- **Primary gaps:** physical experimental data; independent sensors; controlled fault injection; formal consequence-custody rules; external reproduction.

### EA-C007 — Consequence custody

- **Status:** candidate
- **Record type:** retrospective for concept; prospective for formalization and experiments
- **Research questions:** RQ6, RQ8
- **Candidate claim:** post-action resulting-state evidence requires a provenance/custody treatment distinct from request and execution evidence, and causal/consequence conclusions should remain bounded by the quality, independence, timing, and custody of resulting-state observations.
- **Existing evidence:** Ranger, VRX and Evidence Architecture research expansion; EXP-002 scenarios separating request, execution and result.
- **Prior-art boundary:** current action-evidence work already supports action, authority and outcome claims; therefore novelty cannot be claimed for an `outcome` field or for linking an action to an asserted result.
- **Residual research gap:** formal rules and empirical evidence for when a result observation may support a consequence claim, when it must remain merely correlated, and how independent observation/custody changes the verifier's permitted conclusions.
- **Primary gaps:** closest-work survey in cyber-physical assurance/causal provenance; formal definition; prospective digital and physical experiments; independent reproduction.

### EA-C008 — Evidence-aware adversarial qualification

- **Status:** candidate
- **Record type:** prospective
- **Research questions:** RQ7
- **Candidate claim:** security qualification can treat evidence invariants and the provenance of the qualification itself as first-class research objects, enabling reproducible analysis of where evidence claims survive or fail.
- **Existing evidence:** ETS Adversarial Qualification research program; EXP-002 demonstrates the required posture by preserving adverse prior-art findings rather than optimizing for product differentiation.
- **Primary gaps:** executed experiment series; quantitative outcome criteria; external comparison and reproduction.

## Current doctoral contribution hierarchy

The working hierarchy after RATS qualification is:

1. **EA-C003 — formal non-collapse semantics**: highest immediate research priority because it is testable independently of ETS packaging and can be falsified by an equally strong standards profile.
2. **EA-C007 — consequence custody**: highest cyber-physical/AI boundary priority, especially independent result observation and bounded causal attribution.
3. **EA-C006 — cyber-physical decision provenance**: primary empirical platform for EA-C007 and cross-domain validation.
4. **EA-C004 — offline/asynchronous continuity**: technically mature secondary contribution requiring scholarly qualification and refinement evidence.
5. **EA-C002 — relationship-level evidence semantics**: survives only in narrowed form if ordinary PROV extensions do not provide equivalent behavior.
6. **EA-C005 — AI Witness**: treated as a research platform and domain application unless narrower semantics survive current RATS/action-evidence prior art.
7. **EA-C001 — Evidence Object**: treated primarily as engineering substrate unless EXP-001/EXP-003 demonstrates a distinct semantic benefit not attributable to ordinary rich profiles.
8. **EA-C008 — adversarial qualification**: methodological candidate whose value depends on executed and externally reproducible qualification work.

This hierarchy is provisional and must change if external review or prospective experiments produce contrary evidence.

## Promotion rule

A candidate contribution should not become `supported` until, at minimum:

1. relevant prior art is documented;
2. the claimed gap is defensible;
3. a method is explicit;
4. supporting evidence is linked;
5. limitations and counterexamples are recorded;
6. authorship is clear;
7. the contribution can be explained independently of product marketing; and
8. adverse equivalence results from strong standards/profile baselines have been incorporated rather than ignored.
